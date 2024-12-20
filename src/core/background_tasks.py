from typing import Optional, Dict
from datetime import datetime
import asyncio

class BackgroundTaskManager:
    def __init__(self):
        self.tasks: Dict[str, Dict] = {}
        
    async def start_task(self, task_id: str, description: str):
        """Start a new background task"""
        self.tasks[task_id] = {
            'status': 'running',
            'description': description,
            'progress': 0,
            'started_at': datetime.utcnow(),
            'completed_at': None,
            'error': None
        }
    
    async def update_progress(self, task_id: str, progress: float):
        """Update task progress (0-100)"""
        if task_id in self.tasks:
            self.tasks[task_id]['progress'] = progress
    
    async def complete_task(self, task_id: str):
        """Mark task as completed"""
        if task_id in self.tasks:
            self.tasks[task_id]['status'] = 'completed'
            self.tasks[task_id]['completed_at'] = datetime.utcnow()
            self.tasks[task_id]['progress'] = 100
    
    async def fail_task(self, task_id: str, error: str):
        """Mark task as failed"""
        if task_id in self.tasks:
            self.tasks[task_id]['status'] = 'failed'
            self.tasks[task_id]['error'] = error
            self.tasks[task_id]['completed_at'] = datetime.utcnow()
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get current task status"""
        return self.tasks.get(task_id)
    
    def get_active_tasks(self) -> Dict[str, Dict]:
        """Get all active tasks"""
        return {k: v for k, v in self.tasks.items() if v['status'] == 'running'} 