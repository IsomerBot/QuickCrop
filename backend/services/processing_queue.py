"""
Processing queue service for handling image processing jobs
"""

import asyncio
from typing import Dict, Optional, Any
from datetime import datetime
import uuid
from enum import Enum

from services.image_processor import image_processor_service
from services.storage import storage_service
from models.process import CropPreset


class ProcessingStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingJob:
    """Represents a processing job"""
    
    def __init__(self, file_id: str, preset: CropPreset, output_format: str = "jpeg"):
        self.job_id = str(uuid.uuid4())
        self.file_id = file_id
        self.preset = preset
        self.output_format = output_format
        self.status = ProcessingStatus.QUEUED
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.output_path: Optional[str] = None
        self.error: Optional[str] = None
        self.processing_time: Optional[float] = None


class ProcessingQueueService:
    """Service for managing image processing queue"""
    
    def __init__(self):
        self.jobs: Dict[str, ProcessingJob] = {}
        self.queue: asyncio.Queue = asyncio.Queue()
        self.workers: list[asyncio.Task] = []
        self.is_running = False
    
    async def start_workers(self, num_workers: int = 2):
        """Start background workers for processing queue"""
        if self.is_running:
            return
        
        self.is_running = True
        for i in range(num_workers):
            worker = asyncio.create_task(self._process_worker(i))
            self.workers.append(worker)
    
    async def stop_workers(self):
        """Stop all background workers"""
        self.is_running = False
        
        # Cancel all workers
        for worker in self.workers:
            worker.cancel()
        
        # Wait for all workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
    
    async def _process_worker(self, worker_id: int):
        """Worker coroutine for processing jobs"""
        while self.is_running:
            try:
                # Get job from queue with timeout
                job = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                
                # Process the job
                await self._process_job(job)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                continue
    
    async def _process_job(self, job: ProcessingJob):
        """Process a single job"""
        try:
            # Update job status
            job.status = ProcessingStatus.PROCESSING
            job.started_at = datetime.utcnow()
            
            # Load image from storage
            image_bytes = await storage_service.get_upload(job.file_id)
            if not image_bytes:
                raise ValueError(f"File not found: {job.file_id}")
            
            # Load image
            image = image_processor_service.load_image_from_bytes(image_bytes)
            
            # Process crop
            cropped = image_processor_service.process_image_crop(image, job.preset)
            
            # Encode image
            quality = 85 if job.output_format in ['jpeg', 'webp'] else None
            encoded = image_processor_service.encode_image(
                cropped, 
                format=job.output_format,
                quality=quality
            )
            
            # Optimize if PNG
            if job.output_format == 'png':
                encoded = image_processor_service.optimize_png(encoded)
            
            # Save to storage
            suffix = f"_{job.preset.value}_{job.job_id[:8]}"
            output_path = await storage_service.save_output(
                encoded, 
                job.file_id,
                suffix
            )
            
            # Update job status
            job.output_path = output_path
            job.status = ProcessingStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.processing_time = (job.completed_at - job.started_at).total_seconds()
            
        except Exception as e:
            job.status = ProcessingStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.utcnow()
            if job.started_at:
                job.processing_time = (job.completed_at - job.started_at).total_seconds()
    
    async def add_job(self, 
                     file_id: str, 
                     preset: CropPreset,
                     output_format: str = "jpeg") -> str:
        """Add a new processing job to the queue"""
        job = ProcessingJob(file_id, preset, output_format)
        self.jobs[job.job_id] = job
        
        # Add to queue
        await self.queue.put(job)
        
        return job.job_id
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a processing job"""
        job = self.jobs.get(job_id)
        if not job:
            return None
        
        return {
            'job_id': job.job_id,
            'file_id': job.file_id,
            'preset': job.preset.value,
            'status': job.status.value,
            'created_at': job.created_at.isoformat(),
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'output_path': job.output_path,
            'error': job.error,
            'processing_time': job.processing_time
        }
    
    async def process_immediate(self,
                               file_id: str,
                               preset: CropPreset,
                               output_format: str = "jpeg") -> Dict[str, Any]:
        """Process an image immediately without queueing"""
        job = ProcessingJob(file_id, preset, output_format)
        await self._process_job(job)
        return self.get_job_status(job.job_id)


# Singleton instance
processing_queue_service = ProcessingQueueService()