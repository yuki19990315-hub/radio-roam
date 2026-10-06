import json
import os
from game import initial_state, valid_state


class Store:
    """Alternating slots: an interrupted write leaves the previous slot intact."""
    def __init__(self, prefix, validate=valid_state, factory=initial_state):
        self.prefix = prefix
        self.validate = validate
        self.factory = factory

    def load(self):
        candidates = []
        for i in (0, 1):
            try:
                with open(self.prefix + str(i) + '.json') as f:
                    s = json.load(f)
                if self.validate(s):
                    candidates.append(s)
            except (OSError, ValueError, TypeError):
                pass
        return max(candidates, key=lambda s: s['seq']) if candidates else self.factory()

    def save(self, state):
        if not self.validate(state):
            raise ValueError('Invalid save state')
        path = self.prefix + str(state['seq'] % 2) + '.json'
        with open(path, 'w') as f:
            json.dump(state, f)
            f.flush()
        if hasattr(os, 'sync'):
            os.sync()
