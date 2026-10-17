# Mahalanobis distance and outliers

Demo seed. Not a real lecture.

Euclidean distance treats every axis as the same unit. A multivariate Gaussian does not. The Mahalanobis distance asks how many covariance-steps a point sits from mu. In symbols it is the square root of (x - mu) transposed, times Sigma inverse, times (x - mu). Whitening the cloud by Sigma turns that number back into an ordinary Euclidean distance.

A point can look far in raw coordinates and ordinary after whitening, when the shift follows a direction the data already uses. The opposite happens for a small raw shift that cuts across the thin side of the ellipse. Rank points by the Mahalanobis number when you care about the Gaussian cloud. Rank them by Euclidean distance only when Sigma is a multiple of the identity, because then the two rankings match.

An outlier, in this note, means a point whose Mahalanobis distance is larger than a cutoff the course chose in advance. Distance alone does not name the cutoff. A buoy with a huge height and a typical wind can still sit inside the ellipse if height and wind move together. Compare the Mahalanobis number with the cutoff. Do not call the point an outlier because one coordinate looked surprising on its own.
