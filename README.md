# stripe_correction_tools
Scripts to correct for stripe artifacts on UCLA miniscope V4 recordings.

## What is the problem and how does this tool attempt to fix it
During the acquisition of imaging data with the UCLA miniscope V4 certain frames can become compromised and show a pattern where, in a repeated set of rows, the pixels are shifted to a different column index. These shifts appear to be periodic and systematic and might be due to a mis-attribution and / or loss of column indices within a CMOS readout buffer. One of the regularities is that the periodicity of the entire pattern including the compromised buffers (that create the stripe pattern) and the correct ones is consistently smaller than 16200 pixels (27 rows) but a good amount larger than 15600 pixels (26 rows). The specific amount of column shift resulting from this slightly too short periodicity varies between different stripes but it is always negative and divisible by 8. The pattern resets after 26 whenever the column shift would result in negative column values (see more about this in 'find_buffer_indices'.

The tools presented here first identify the boundaries of the different stripes by first detecting abrupt changes in pixel intensities and then reconstructing all the boundaries by exploiting the regularities introduced above. To correct the image, first, the best circular shift of all the compromised buffers concatenated is found and applied. This often leads to a positional shift of the stripes on the vertical axis. Then, within each individual stripe the best circular shift is found and applied.

There seem to be at least two types of striping. The first one is a static shift of one of the buffers with respect to the other one leading to a pattern of alternating stripes. This striping can be corrected fairly well using the current tools:

<img width="3000" height="1440" alt="Static_stripes" src="https://github.com/user-attachments/assets/f0d841b6-2414-4deb-9171-ec4eb44b5219" />

The second type of stripes look like the pattern is traveling across the image from right to left. For this type of artifact there are often multiple shifted stripes present and it appears as if individual stripes are not only shifting with respect to the intact rows but also in relation to the other corrupted stripes. The tools presented here can usually not fix this kind of artifact but still improves the quality of the image.
Here is an example of a frame that could be reconstructed relatively well:

<img width="3000" height="1440" alt="dynamic_stripes_partially_successful" src="https://github.com/user-attachments/assets/e3cb5e8c-5830-46fa-bd14-ea2fa5773097" />

Whereas for this frame the correction was less successful:

<img width="3000" height="1440" alt="dynamic_stripes_unsuccessful" src="https://github.com/user-attachments/assets/5adbf2a6-d1df-4c0d-974c-969003fb7227" />

Typically, frames with different kinds of artifacts that don't show the strong periodicity at around 27 rows are not detected. Here is an example of a frame with a more isolated row artifact that does not show the regularities found on the striped frames:

<img width="1920" height="1440" alt="Non-periodic_artifact" src="https://github.com/user-attachments/assets/a4da8057-d5e1-4e77-a84f-9a2be6af9555" />


## Limitations
While the functions introduced here can dramatically improve the quality of corrupted frames the cannot completely restore the original image. Better to prevent these stripes than to fix them! Make sure to test the integrity of the coax cable and and to replace it if necessary. Consider externally powering the DAQ using a 6V input to minimize power fluctuations.

## Installation
Simply clone the repo. Add this repo to you current python path via sys and import the desired functions.

Please reach out for questions, problems and improvements!
LO, August 6, 2026



