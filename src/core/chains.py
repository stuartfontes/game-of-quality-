class Chain:
    def __init__(self, anchor_x, anchor_y, length):
        self.anchor_x = anchor_x
        self.anchor_y = anchor_y
        self.length = length

    @property
    def tip(self):
        return (self.anchor_x, self.anchor_y + self.length)