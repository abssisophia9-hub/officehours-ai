# Parametric methods

Demo seed. Not a real lecture.

A parametric method chooses a family of shapes first, then a short list of numbers that picks one shape from that family. Call that list theta. Its length is fixed before any row of data arrives. Fitting only fills those numbers in. Collecting more rows does not add new slots to theta.

A one-dimensional Gaussian with an unknown center and an unknown spread is parametric: two numbers, however long the sample is. A histogram that keeps a bin count for every new value is not parametric in this sense, because the description grows with the sample.

The harbor-buoy example uses one number for the typical wave height and one number for how widely the heights wander. Those two numbers are the whole model. A new morning of measurements updates them. It does not invent a third parameter.

What the method does not do is claim the family was true. If the heights are lopsided and the family is symmetric, a well-fit theta still describes the wrong shape. The check is whether new heights land where the fitted family said they would, not whether the arithmetic finished.
