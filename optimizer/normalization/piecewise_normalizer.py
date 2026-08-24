from optimizer.normalization.normalizer import Normalizer


class PiecewiseNormalizer(Normalizer):

    def __init__(

        self,

        points

    ):

        """
        points:

        [

            (0,100),

            (25,98),

            (50,95),

            ...

        ]
        """

        self.points = sorted(points)

    def normalize(self, value):

        if value <= self.points[0][0]:
            return self.points[0][1]

        for i in range(

            len(self.points)-1

        ):

            x1,y1 = self.points[i]

            x2,y2 = self.points[i+1]

            if x1 <= value <= x2:

                ratio = (

                    value-x1

                )/(x2-x1)

                return y1 + ratio*(y2-y1)

        return self.points[-1][1]
