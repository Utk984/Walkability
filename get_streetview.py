import asyncio
import os
import pandas as pd
import numpy as np
from aiohttp import ClientSession, TCPConnector, ClientError
from PIL import Image
from transformers import AutoImageProcessor, SegformerForSemanticSegmentation
from streetlevel import streetview
import torch
from tqdm import tqdm
import json
from shapely.geometry import shape, Point
import time
from functools import lru_cache

# Load segmentation model
device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
print(f"Using device: {device}")

# Load model only once and keep in memory
processor = AutoImageProcessor.from_pretrained("nvidia/segformer-b0-finetuned-cityscapes-1024-1024")
model = SegformerForSemanticSegmentation.from_pretrained("nvidia/segformer-b0-finetuned-cityscapes-1024-1024")
model = model.to(device)
model.eval()

# Create a batch processing function for the model
def process_images_batch(image_batch, batch_size=4):
    results = []
    for i in range(0, len(image_batch), batch_size):
        batch = image_batch[i:i+batch_size]
        inputs = processor(images=batch, return_tensors="pt")
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = model(**inputs)
        
        preds = outputs.logits.argmax(dim=1).cpu().numpy()
        
        for pred in preds:
            total = pred.size
            gvi = 100 * np.sum(pred == 8) / total  # vegetation
            svf = 100 * np.sum(pred == 10) / total  # sky
            results.append((gvi, svf))
            
    return results

# Cache the boundary check for performance
@lru_cache(maxsize=10000)
def is_within_chandigarh(lat: float, lon: float) -> bool:
    """Return True if (lat, lon) lies inside the exact Chandigarh boundary."""
    return city_poly.contains(Point(lon, lat))

# Load city boundary
with open("boundary.geojson") as f:
    gj = json.load(f)
    city_poly = shape(gj["features"][0]["geometry"])

# Load existing data and initialize tracking sets
print("Loading existing data...")
try:
    existing_df = pd.read_csv("chandigarh_panos.csv")
    visited_ids = set(existing_df["id"].to_list())
    panorama_data = existing_df.to_dict(orient="records")
    print(f"{len(visited_ids)} existing panoramas loaded")
except FileNotFoundError:
    visited_ids = set()
    panorama_data = []
    print("No existing data found, starting fresh")

# Queue for saving data periodically
save_queue = asyncio.Queue()

# Semaphore to limit concurrent network requests
sem = asyncio.Semaphore(20)  # Adjust based on your network capacity

async def fetch_with_semaphore(coro):
    """Limit concurrent network operations"""
    async with sem:
        try:
            return await coro
        except (json.JSONDecodeError, ClientError, asyncio.TimeoutError) as e:
            # print(f"Network error: {str(e)[:100]}...")
            return None
        except Exception as e:
            # print(f"Unexpected error: {str(e)[:100]}...")
            return None

async def save_data_worker():
    """Worker to save data periodically without blocking main crawl"""
    while True:
        # Wait for signal to save
        await save_queue.get()
        
        try:
            df = pd.DataFrame(panorama_data).drop_duplicates("id")
            df.to_csv("chandigarh_panos.csv", index=False)
            print(f"✓ Saved progress: {len(df)} panoramas")
        except Exception as e:
            print(f"Error saving data: {e}")
        
        save_queue.task_done()

async def process_pano_batch(pano_batch, queue, session):
    """Process a batch of panoramas concurrently"""
    # Fetch all panorama details concurrently

    if isinstance(pano_batch[0], str):
        full_panos = await asyncio.gather(*[
            fetch_with_semaphore(streetview.find_panorama_by_id_async(id, session))
            for id in pano_batch
        ])
    else:
        full_panos = await asyncio.gather(*[
            fetch_with_semaphore(streetview.find_panorama_by_id_async(pano.id, session))
            for pano in pano_batch
        ])
    
    # Filter valid panoramas
    valid_panos = []
    neighbor_panos = []
    
    for full_pano in full_panos:
        if not full_pano or not full_pano.image_sizes:
            continue

        # Add neighbors to queue
        for neighbor in full_pano.neighbors:
            if neighbor.id not in visited_ids and neighbor.id not in queue and neighbor not in full_panos and is_within_chandigarh(neighbor.lat, neighbor.lon):
                neighbor_panos.append(neighbor)

        # Skip invalid or already visited
        if full_pano.id in visited_ids or not is_within_chandigarh(full_pano.lat, full_pano.lon):
            continue
            
        valid_panos.append(full_pano)
    
    # Fetch all panorama images concurrently
    images = []
    if valid_panos:
        images = await asyncio.gather(*[
            fetch_with_semaphore(streetview.get_panorama_async(pano, session))
            for pano in valid_panos
        ])
    
    # Process all images in batch for better GPU utilization
    if images:
        gvi_svf_results = process_images_batch(images)
        
        # Save results
        for pano, (gvi, svf) in zip(valid_panos, gvi_svf_results):
            visited_ids.add(pano.id)
            panorama_data.append({
                "id": pano.id,
                "lat": pano.lat,
                "lon": pano.lon,
                "elevation": pano.elevation,
                "date": f"{pano.date.year}-{pano.date.month:02d}" if pano.date else None,
                "gvi": gvi,
                "svf": svf
            })
    
    return neighbor_panos

async def crawl_panoramas(session, start_lat, start_lon):
    start_time = time.time()
    processed_count = len(visited_ids)
    batch_size = 32  # Process panoramas in batches
    
    # Start with initial panoramas
    if len(existing_df) > 0:
        queue = existing_df["id"].to_list()
    else:
        initial_panos = await streetview.get_coverage_tile_by_latlon_async(30.7251, 76.7992, session)
        queue = list(initial_panos)

    # Start progress tracking
    pbar = tqdm(desc="Processing panoramas", unit="panos")
    
    last_save = time.time()
    
    while queue:
        # Take a batch from the queue
        batch = queue[:batch_size]
        queue = queue[batch_size:]
        
        # Process the batch
        new_neighbors = await process_pano_batch(batch, queue, session)
        
        # Add new neighbors to queue
        queue.extend(new_neighbors)
        
        # Update progress
        new_processed = len(visited_ids) - processed_count
        processed_count = len(visited_ids)
        pbar.update(new_processed)

        print(f"\r{len(queue)} panoramas left", end = "", flush=True)
        
        # Save progress every 2 minutes or every 100 new panoramas
        if (time.time() - last_save > 120 or new_processed >= 100) and new_processed > 0:
            if save_queue.empty():
                await save_queue.put(True)
            last_save = time.time()
    
    pbar.close()
    
    # Final save
    if save_queue.empty():
        await save_queue.put(True)
    await save_queue.join()
    
    print(f"✓ Completed in {time.time() - start_time:.1f} seconds")
    print(f"✓ Processed {len(visited_ids)} panoramas total")

async def main():
    # Starting coordinates
    start_lat, start_lon = 30.701941, 76.772567
    
    # Use a larger connection pool with keep-alive
    connector = TCPConnector(limit=100, ttl_dns_cache=300)
    
    async with ClientSession(connector=connector) as session:
        # Start the background saver task
        save_task = asyncio.create_task(save_data_worker())
        
        try:
            # Start the main crawler
            await crawl_panoramas(session, start_lat, start_lon)
        finally:
            # Ensure final data is saved
            if save_queue.empty():
                await save_queue.put(True)
            await save_queue.join()
            
            # Cancel the save worker
            save_task.cancel()
            try:
                await save_task
            except asyncio.CancelledError:
                pass
    
    # Final save to ensure everything is written
    df = pd.DataFrame(panorama_data).drop_duplicates("id")
    df.to_csv("chandigarh_panos.csv", index=False)
    print(f"✓ Final save complete: {len(df)} panoramas.")

if __name__ == "__main__":
    # Increase default timeout for asyncio
    asyncio.run(main(), debug=False)