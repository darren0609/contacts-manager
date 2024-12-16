from typing import List
from .commands import Command

class CommandManager:
    def __init__(self):
        self.undo_stack: List[Command] = []
        self.redo_stack: List[Command] = []
    
    async def execute(self, command: Command):
        """Execute a command and add it to the undo stack"""
        await command.execute()
        self.undo_stack.append(command)
        self.redo_stack.clear()  # Clear redo stack when new command is executed
    
    async def undo(self) -> bool:
        """Undo the last command"""
        if not self.undo_stack:
            return False
        
        command = self.undo_stack.pop()
        await command.undo()
        self.redo_stack.append(command)
        return True
    
    async def redo(self) -> bool:
        """Redo the last undone command"""
        if not self.redo_stack:
            return False
        
        command = self.redo_stack.pop()
        await command.execute()
        self.undo_stack.append(command)
        return True
    
    def can_undo(self) -> bool:
        return bool(self.undo_stack)
    
    def can_redo(self) -> bool:
        return bool(self.redo_stack)
    
    def get_undo_description(self) -> str:
        return self.undo_stack[-1].description if self.undo_stack else ""
    
    def get_redo_description(self) -> str:
        return self.redo_stack[-1].description if self.redo_stack else "" 