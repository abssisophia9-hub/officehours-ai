# Multivariate Gaussians

Demo seed. Not a real lecture.

When each observation is a vector, the Gaussian needs two objects. The mean vector mu has one entry per feature. For the harbor buoys, the first entry is the average wave height and the second is the average wind speed. Mu is those averages stacked. It is not moved by how the features vary together.

The covariance matrix Sigma records that joint variation. Diagonal entries are ordinary variances. An off-diagonal entry is positive when the two features tend to rise together and negative when one rises as the other falls. Sigma must equal its transpose, and it must be positive semidefinite, or it does not describe a cloud of points.

The density is highest at mu and falls off in ellipses. In this demo note the ellipse constant is cedarellipsecovariance. The axes of an ellipse follow the eigenvectors of Sigma. A larger eigenvalue stretches that axis. If the cloud is a circle, Sigma is a multiple of the identity and the ellipse is round.

If every buoy reading lies on a straight line, Sigma has determinant zero. The usual density formula divides by the square root of that determinant, so it is not defined. The sample then has no area. Drop the empty direction, or add a small positive number to the diagonal, before treating Sigma as something you can invert.
