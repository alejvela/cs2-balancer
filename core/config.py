import yaml


class Config:

    def __init__(self, file):

        with open(file, encoding="utf8") as f:
            self.data = yaml.safe_load(f)

    @property
    def teams(self):
        return self.data["teams"]

    @property
    def weights(self):
        return self.data["weights"]

    @property
    def constraints(self):
        return self.data["constraints"]
