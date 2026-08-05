#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug  4 13:15:39 2026

@author: loesch
"""

def are_stripes_present(frame, reference, min_std = 8, min_stripe_num = 10, density_threshold = 0.15):
    '''Check whether a frame has the striping pattern
    
    Inputs
    ------
    frame: array, image frame to check for stripe pattern
    reference: array, an intact image as a reference, by preference occuring close
               in time to the frame in question
    min_std: int, threshold for detection of border between stripes, in units of
             standard deviations of the diff from the reference image
    min_stripe_num: int, minimum number of stripes that need to be present
    
    Outputs
    -------
    stripes_present: bool, flag for whether the image is corrupted
    
    --------------------------------------------------------------------------
    '''
    import numpy as np
    from scipy.signal import welch, find_peaks
    
    # #Compute diffs of the images
    # reg_diff = np.diff(np.mean(reference,axis=1))
    # str_diff = np.diff(np.mean(frame,axis=1))
    
    # thresh = min_std * np.std(np.abs(reg_diff))
    # stripes_present = np.sum(np.abs(str_diff) > thresh) > min_stripe_num # More than five simultaneous jumps
    
    frequencies, psd_values = welch(np.mean(frame,axis=1) - np.mean(reference,axis=1), fs = 600, nfft = 600)
    # peak_freq = frequencies[np.argmax(psd_values)] #Found frequency marks the bottom of the 1 Hz frequency bin
    # stripes_present = (peak_freq == 22) & (psd_values[int(peak_freq)] >= 0.1) 
    #This is because 600/27 = 22.22 -> pattern has to repeat after 27ish lines
    
    peaks, _ = find_peaks(psd_values, distance = 10)
    stripes_present = ((22 in peaks) or (23 in peaks)) & (psd_values[22] > density_threshold) & (frequencies[np.argmax(psd_values)] > 20)
    
    return stripes_present

#%%

def find_buffer_indices(frame, reference, min_std = 5):
    '''Find the offsets of the image buffers. These mark the borders between 
    the different stripes.
    NOTE: In the current state this function is hard-coded for full frame images
    with the V4 miniscope. It thus assumes image dimensions to be 600 x 600 pixels
    and the number of rows per full set of buffers ~ 16160 to be between 26 and 
    27 rows of pixels (closer to 27).
      
    Inputs
    ------
    frame: array, image frame to check for stripe pattern
    reference: array, an intact image as a reference, by preference occuring close
               in time to the frame in question
    min_std: int, threshold for detection of border between stripes, in units of
             standard deviations of the diff from the reference image
             
    Outputs
    -------
    full_stripe_indices: list of n x 2 arrays, each element of the list is one set of
                         stripes. Each consecutive onset of these is shifted
                         in a regular manner. Array rows are the individual offsets,
                         column 0 represents the row index, column 1 the column
                         index on the frame.
    buffers: array, linearized and sorted indices for all the stripes that are
             shifted with respect to the reference image. Column 0 is the onset,
             column 1 the last index of that buffer
    ---------------------------------------------------------------------------
    '''
    
    import numpy as np
    from scipy.stats import mode
    
    
    reference = reference.astype(float)
    frame = frame.astype(float)
    
    #First, find rows with expected jumps. These are defined by having a higher
    #than expected jump in the rightward and downward direction of the image and
    #no jumps in the upward and leftward direction
    candidate_positions = [[],[]]
    thresh = np.std(np.diff(reference)) * min_std
    for row in range(1, frame.shape[0]-1):
        for column in range(1, frame.shape[1]-1):
            right = np.abs(frame[row,column] - frame[row,column+1])
            down = np.abs(frame[row,column] - frame[row+1,column])
            left = np.abs(frame[row,column] - frame[row,column-1])
            up = np.abs(frame[row,column] - frame[row-1,column])
       
            if ((right > thresh) & (down > thresh)) & ((left <= thresh) & (up <= thresh)):
                candidate_positions[0].append(row)
                candidate_positions[1].append(column)
        
    #Iteratively find related onsets, first rule, decreasing by a fixed amount, second rule roughly 26 lines difference
    stripe_indices = []
    cp_copy = np.squeeze(candidate_positions).T
    
    while (cp_copy.shape[0] > 0):
        test_pos = cp_copy[0,0]
        expected_rows = []
        for k in range(int(((frame.shape[0] - test_pos)+27) / 27)):
            expected_rows.append(test_pos + 27 * k)
        
        one_stripe = [0]
        for k in range(1, len(expected_rows)):
            tmp = np.where(cp_copy[:,0] == expected_rows[k])[0] #Check for expected rows in candidate events
            if tmp.shape[0] > 0:
                if cp_copy[tmp[0],1] < cp_copy[one_stripe[-1],1]: # Make sure that the column number shrinks
                    one_stripe.append(tmp[0])
            elif tmp.shape[0] == 0:
                if np.where(cp_copy[:,0] == expected_rows[k]-1)[0].shape[0] > 0: #When there are only 26 lines because of a line break
                    tmp = np.where(cp_copy[:,0] == expected_rows[k]-1)[0]
                    if cp_copy[tmp[0],1] > candidate_positions[1][one_stripe[-1]]: # Make sure to only skip 26 lines when there is a break
                        one_stripe.append(tmp[0])
                        expected_rows[k:] = np.array(expected_rows[k:]) - 1 #Subtract the lost row from all the following 
                else:
                    pass
        
        stripe_indices.append(cp_copy[np.array(one_stripe)])
        cp_copy = np.delete(cp_copy, np.array(one_stripe),axis=0)
    
    stripe_indices = [x for x in stripe_indices if len(x) >1] #Only retain stripe offsets that can be matched
    
    #Okay, now that we have identified how many stripes there are and what the most obvious onsets are
    #we need to complete the onset reconstruction. To do this we first find by how many
    #pixels the pattern is offset after going through all the stripes, thus the
    #column difference between the position at row - 27 and the current row
    #while this value is variable it always is divisible by 8. Whenever the shift
    #crosses 0 we have a 26 line pattern with the remainder difference subtracted
    #from 600 plus 8 (which adds this felt irregularity). Example the last position
    #is line 498 and column 23 with a shift of -48 pixels. The next position will thus
    #be line 524 (so, only 26 lines) and column 583 (600 + (23 - 48) + 8).
    
    #Knowing this pattern for every stripe we can reconstruct all the missing positions
    #in forward and backward direction.
    full_stripe_indices = [np.empty([1,2]) for x in range(len(stripe_indices))] #Super ugly: create another list to add to
    for k in range(len(stripe_indices)):
        twentyseven_liner = np.where(np.diff(stripe_indices[k][:,0]) == 27)[0]
        column_shift = mode(np.diff(stripe_indices[k][:,1])[twentyseven_liner])[0] #take the most frequent value, there might be some weird outliers...
        assert (column_shift < 0) & (column_shift % 8 == 0), "Column shift is either positive or not divisible by 8"
        
        #Start the reconstruction
        full_stripe_indices[k][0,:] = stripe_indices[k][0,:] #Initialize
        
        #Backward direction: if we are missing stripe transitions before
        if stripe_indices[k][0,0] > 27: #In this case we should be missing buffer transitions earlier
            loops = np.floor(stripe_indices[k][0,0] / ((600 * 27 + column_shift)/600)).astype(int) #Take into account that the pattern repeats at a little less than 27 lines...
            for lo in range(loops):
                if full_stripe_indices[k][0,1] - column_shift < 600:
                    full_stripe_indices[k] = np.vstack((np.array([full_stripe_indices[k][0,0]-27, full_stripe_indices[k][0,1] - column_shift]), full_stripe_indices[k]))
                elif full_stripe_indices[k][0,1] - column_shift >= 600:
                    full_stripe_indices[k] = np.vstack((np.array([full_stripe_indices[k][0,0]-26, full_stripe_indices[k][0,1] - column_shift - 600 - 8]), full_stripe_indices[k]))
        
        #Forward direction: all the missing transitions after the first detected one
        for n in range(1, stripe_indices[k].shape[0]):
            #First, if the expected line has been found
            if ((stripe_indices[k][n,0] - stripe_indices[k][n-1,0] == 27) & (stripe_indices[k][n-1,1] + column_shift >= 0)) or \
                ((stripe_indices[k][n,0] - stripe_indices[k][n-1,0] == 26) & (stripe_indices[k][n-1,1] + column_shift < 0)):
                    full_stripe_indices[k] = np.vstack((full_stripe_indices[k], stripe_indices[k][n,:]))
            else: #When we are missing a position marker
                loops = np.round((stripe_indices[k][n,0] - stripe_indices[k][n-1,0]) / ((600 * 27 + column_shift)/600)).astype(int) -1
                #Take into account that the pattern repeats at a little less than 27 lines and that we have the next timepoint
                for lo in range(loops):
                    if full_stripe_indices[k][-1,1] + column_shift >= 0:
                        full_stripe_indices[k] = np.vstack((full_stripe_indices[k], np.array([full_stripe_indices[k][-1,0] + 27, full_stripe_indices[k][-1,1] + column_shift])))
                    elif full_stripe_indices[k][-1,1] + column_shift < 0:
                        full_stripe_indices[k] = np.vstack((full_stripe_indices[k], np.array([full_stripe_indices[k][-1,0] + 26, 600 + full_stripe_indices[k][-1,1] + column_shift + 8])))
                
                #Finally add the current position after having accounted for the missing ones
                full_stripe_indices[k] = np.vstack((full_stripe_indices[k], stripe_indices[k][n,:]))
        
        #Now check if we are missing some positions at the end
        if full_stripe_indices[k][-1,0] + 27 < 600:
            loops = np.floor((600 - full_stripe_indices[k][-1,0]) / ((600 * 27 + column_shift)/600)).astype(int) #Take into account that the pattern repeats at a little less than 27 lines...
            for lo in range(loops):
                if full_stripe_indices[k][-1,1] + column_shift >= 0:
                    full_stripe_indices[k] = np.vstack((full_stripe_indices[k], np.array([full_stripe_indices[k][-1,0] + 27, full_stripe_indices[k][-1,1] + column_shift])))
                elif full_stripe_indices[k][-1,1] + column_shift < 0:
                    full_stripe_indices[k] = np.vstack((full_stripe_indices[k], np.array([full_stripe_indices[k][-1,0] + 26, 600 + full_stripe_indices[k][-1,1] + column_shift + 8])))
            
    #Make sure to exclude one kind of stripe if it basically captures the same
    #lines as an already existing one. Take the one with more detected transitions
    is_duplicate = []
    ind = [] #The comparison
    for k in range(len(full_stripe_indices)-1):
        for n in range(k+1, len(full_stripe_indices)):
            tmp = [0]
            ind.append(np.array([k,n]))
            for q in range(full_stripe_indices[k].shape[0]):
                if full_stripe_indices[k][q,0] in full_stripe_indices[n][:,0]:
                    tmp.append(1)
            is_duplicate.append(np.sum(tmp))
    ind = np.vstack(ind)
    tmp = np.where(np.array(is_duplicate) > 0)[0]
    if tmp.shape[0] > 0:
        drop = []
        for k in tmp:
           drop.append(ind[k,np.argmin([stripe_indices[ind[k,0]].shape[0], stripe_indices[ind[k,1]].shape[0]])])
        full_stripe_indices= [full_stripe_indices[x] for x in range(len(full_stripe_indices)) if x not in drop]
    
    #Generate the linearized buffer transisition indices
    linearized_buffer_index = np.sort(np.squeeze(np.vstack([-1] + [x[0]*600 + x[1] for x in np.vstack(full_stripe_indices)]) +1)).astype(int) #Add one to convert to onsets rather than offsets
    #Generate the buffer onsets and offsets
    buffers = np.zeros([linearized_buffer_index.shape[0], 2]) * np.nan
    for k in range(linearized_buffer_index.shape[0]-1):
        buffers[k,0] = linearized_buffer_index[k]
        buffers[k,1] = linearized_buffer_index[k+1]-1
    buffers[-1,0] = linearized_buffer_index[-1]
    buffers[-1,1] = 600 * 600
    
    #Find out which one of the stripes is the unshifted version by finding the stripe with lowest std between reference and striped image
    diff_im = (frame - reference).flatten()
    std_dif = []
    for k in range(len(full_stripe_indices)):
        std_dif.append(np.std(diff_im[linearized_buffer_index[k]:linearized_buffer_index[k+1]]))
    correct_id = np.argmin(std_dif)
    remove_buffers = np.arange(correct_id, buffers.shape[0], len(full_stripe_indices))
    
    buffers = np.delete(buffers, remove_buffers, axis=0).astype(int)
    
    return full_stripe_indices, buffers

#%%---Now find the optimal shifts for the remaining buffers and correct the image

def shift_stripes(frame, reference, full_stripe_indices, buffers):
    '''Finds optimal shifts for the stripes and applies them to the image.
    This function performs two sets of shifts, one is done over the concatenated
    buffers of each kind of stripe, and an additional one is applied for each
    individual buffer.
    
    Inputs
    ------
    frame: array, image frame to check for stripe pattern
    reference: array, an intact image as a reference, by preference occuring close
               in time to the frame in question
    min_std: int, threshold for detection of border between stripes, in units of
             standard deviations of the diff from the reference image
    full_stripe_indices: list of n x 2 arrays, each element of the list is one set of
                         stripes. Each consecutive onset of these is shifted
                         in a regular manner. Array rows are the individual offsets,
                         column 0 represents the row index, column 1 the column
                         index on the frame.
    buffers: array, linearized and sorted indices for all the stripes that are
             shifted with respect to the reference image. Column 0 is the onset,
             column 1 the last index of that buffer
             
    Outputs
    -------
    reconstructed_frame: array, the corrected frame
    ---------------------------------------------------------------------------
    '''
    
    import numpy as np
    from scipy.signal import correlate, correlation_lags

    stripe_im = np.array(frame.astype(float).flatten())
    ref_im = np.array(reference.astype(float).flatten())
    
    # #First concatenate all the bad buffers and shift all to find the best row
    # #indices
    # joint_buffers = np.hstack([np.arange(buffers[x,0], buffers[x,1]+1) for x in range(buffers.shape[0])])
    # if joint_buffers[-1] == 600*600:
    #     joint_buffers = joint_buffers[:-1]
    # lags = correlation_lags(joint_buffers.shape[0], joint_buffers.shape[0])
    # corr = correlate(stripe_im[joint_buffers], ref_im[joint_buffers], mode = 'full', method='fft')
    # shift = -lags[np.argmax(corr)]
    
    # stripe_im[joint_buffers] = np.roll(stripe_im[joint_buffers], shift)
        
    # #Second, shift within each buffer to the best position
    # for k in range(buffers.shape[0]):
    #     lags = correlation_lags(buffers[k,1] +1   - buffers[k,0], buffers[k,1] + 1 - buffers[k,0])
    #     corr = correlate(stripe_im[buffers[k,0]:buffers[k,1]+1], ref_im[buffers[k,0]:buffers[k,1]+1], mode = 'full', method='fft')
    #     shift = -lags[np.argmax(corr)]
        
    #     stripe_im[buffers[k,0]:buffers[k,1]+1] = np.roll(stripe_im[buffers[k,0]:buffers[k,1]+1], shift)
    
    
    #Use correlation on circularly shifted trace rather than regular cross-correlation
    def periodic_corr(x, y):
        """Periodic correlation, implemented using the FFT.

        x and y must be real sequences with the same length.
        """
        from numpy.fft import fft, ifft
        return ifft(fft(x) * fft(y).conj()).real
    
    #First concatenate all the bad buffers and shift all to find the best row
    #indices
    joint_buffers = np.hstack([np.arange(buffers[x,0], buffers[x,1]+1) for x in range(buffers.shape[0])])
    if joint_buffers[-1] == 600*600:
        joint_buffers = joint_buffers[:-1]
    corr = periodic_corr(stripe_im[joint_buffers], ref_im[joint_buffers])
    
    shift = joint_buffers.shape[0] - np.argmax(corr)
    stripe_im[joint_buffers] = np.roll(stripe_im[joint_buffers], shift)
        
    #Second, shift within each buffer to the best position
    for k in range(buffers.shape[0]):
      corr = periodic_corr(stripe_im[buffers[k,0]:buffers[k,1]+1], ref_im[buffers[k,0]:buffers[k,1]+1])
      shift = (buffers[k,1]+1 - buffers[k,0]) - np.argmax(corr)
        
      stripe_im[buffers[k,0]:buffers[k,1]+1] = np.roll(stripe_im[buffers[k,0]:buffers[k,1]+1], shift)
    

    reconstructed_frame = np.reshape(stripe_im, [600, 600])
    return reconstructed_frame
