# services/decorators.py
import functools


def autosave(func):
    """
    Decorator that automatically calls repo.save() after the decorated method executes.
    Assumes the class instance (self) has a 'repo' attribute with a 'save' method.
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # 1. Execute the actual logic (e.g., create_goal)
        result = func(self, *args, **kwargs)

        # 2. Auto-save to disk
        if hasattr(self, 'repo') and hasattr(self.repo, 'save'):
            print(f"💾 Auto-saving after {func.__name__}...")
            self.repo.save()

        return result

    return wrapper