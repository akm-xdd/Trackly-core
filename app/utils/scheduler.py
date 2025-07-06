import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
import atexit
from datetime import datetime

from app.services.stats.service import run_daily_aggregation

# Set up logging
logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.INFO)
logger = logging.getLogger(__name__)


class SchedulerManager:
    """Manages background job scheduling"""
    
    def __init__(self):
        self.scheduler = None
        self._setup_scheduler()
    
    def _setup_scheduler(self):
        """Initialize the scheduler with Windows-compatible settings"""
        # Use MemoryJobStore for simplicity and Windows compatibility
        jobstores = {
            'default': MemoryJobStore()
        }
        
        # Configure scheduler with conservative settings for Windows
        job_defaults = {
            'coalesce': False,  # Don't combine multiple missed executions
            'max_instances': 1,  # Only one instance of each job at a time
            'misfire_grace_time': 300  # 5 minutes grace period for missed jobs
        }
        
        # Create BackgroundScheduler (works well on Windows)
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            job_defaults=job_defaults,
            timezone='UTC'  # Use UTC to avoid Windows timezone issues
        )
        
        logger.info("Scheduler initialized with Windows-compatible settings")
    
    def start_scheduler(self):
        """Start the background scheduler"""
        if self.scheduler and not self.scheduler.running:
            try:
                self.scheduler.start()
                logger.info("Background scheduler started successfully")
                
                # Schedule the daily aggregation job
                self._schedule_daily_aggregation()
                
                # Register shutdown handler for graceful cleanup
                atexit.register(self.shutdown_scheduler)
                
            except Exception as e:
                logger.error(f"Failed to start scheduler: {str(e)}")
                raise e
    
    def _schedule_daily_aggregation(self):
        """Schedule the 30-minute aggregation job"""
        try:
            # Add the job to run every 30 minutes
            self.scheduler.add_job(
                func=run_daily_aggregation,
                trigger=IntervalTrigger(minutes=int(os.getenv('STATS_AGGREGATION_INTERVAL_MINUTES', 30))),
                id='daily_stats_aggregation',
                name='Daily Stats Aggregation Job',
                replace_existing=True,
                coalesce=True, 
                max_instances=1 
            )
            
            # Optional: Also schedule at specific times (e.g., every hour at minute 0 and 30)
            # Uncomment the lines below if you prefer cron-style scheduling
            # self.scheduler.add_job(
            #     func=run_daily_aggregation,
            #     trigger=CronTrigger(minute='0,30'),  # Run at :00 and :30 of each hour
            #     id='hourly_stats_aggregation',
            #     name='Hourly Stats Aggregation Job',
            #     replace_existing=True,
            #     coalesce=True,
            #     max_instances=1
            # )
            
            logger.info("Daily aggregation job scheduled to run every 30 minutes")
            
            # Run once immediately to populate initial data
            logger.info("Running initial aggregation...")
            run_daily_aggregation()
            
        except Exception as e:
            logger.error(f"Failed to schedule daily aggregation job: {str(e)}")
            raise e
    
    def shutdown_scheduler(self):
        """Gracefully shutdown the scheduler"""
        if self.scheduler and self.scheduler.running:
            try:
                logger.info("Shutting down background scheduler...")
                self.scheduler.shutdown(wait=True)
                logger.info("Background scheduler shut down successfully")
            except Exception as e:
                logger.error(f"Error shutting down scheduler: {str(e)}")
    
    def get_job_status(self):
        """Get status of scheduled jobs"""
        if not self.scheduler:
            return {"status": "not_initialized"}
        
        if not self.scheduler.running:
            return {"status": "stopped"}
        
        jobs = []
        for job in self.scheduler.get_jobs():
            next_run = job.next_run_time.isoformat() if job.next_run_time else None
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": next_run,
                "trigger": str(job.trigger)
            })
        
        return {
            "status": "running",
            "jobs": jobs,
            "scheduler_state": "running" if self.scheduler.running else "stopped"
        }
    
    def trigger_manual_aggregation(self):
        """Manually trigger the aggregation job"""
        try:
            logger.info("Manually triggering daily aggregation...")
            result = run_daily_aggregation()
            logger.info(f"Manual aggregation completed: {result}")
            return result
        except Exception as e:
            logger.error(f"Manual aggregation failed: {str(e)}")
            raise e


# Global scheduler instance
scheduler_manager = SchedulerManager()


# Convenience functions for FastAPI integration
def start_background_scheduler():
    """Start the background scheduler (call from FastAPI startup)"""
    scheduler_manager.start_scheduler()


def stop_background_scheduler():
    """Stop the background scheduler (call from FastAPI shutdown)"""
    scheduler_manager.shutdown_scheduler()


def get_scheduler_status():
    """Get scheduler status (for API endpoint)"""
    return scheduler_manager.get_job_status()


def manual_trigger_aggregation():
    """Manually trigger aggregation (for API endpoint)"""
    return scheduler_manager.trigger_manual_aggregation()