    def save_offset(self):
        ann = self.annotation
        self.ox, self.oy = ann.get_transform().transform(ann.xyann)
