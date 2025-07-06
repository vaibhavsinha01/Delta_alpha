class SignalMemory:
    def __init__(self):
        self.memory = set()

    def has_traded(self, signal_id):
        return signal_id in self.memory

    def mark_traded(self, signal_id):
        self.memory.add(signal_id)

    def reset(self):
        self.memory.clear()
