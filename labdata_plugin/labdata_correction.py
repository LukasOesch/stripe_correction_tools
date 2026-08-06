from labdata.schema import *

@get_user_schema()
class MiniscopeStripeCorrection(dj.Computed):
    definition = '''
    -> Miniscope
    ---
    num_frames_changed = 0       : int
    changed_frame_indices = NULL : longblob       # the frames that had to be corrected
    previous_checksum = NULL     : varchar(32)    # checksum of the processed file
    '''
    
    def check_session(self,key):
        '''
        Method to run through the image stack and find frames that show a pattern
        of repeating horizontal stripes.
        '''
        stack = (Miniscope & key).open()
        reference = stack[0,:,:] #We use the first frame of the recording as a
        #static reference for the detection. We can do this because we are 
        #averaging over columns for the initial detection of stripes along the 
        #the rows.
        stripe_frame_idx = []
        frame_idx = 0
        for ind in tqdm(chunk_indices(stack.shape[0])):
            substack = stack[ind[0]:ind[1],:,:]
            for k in range(substack.shape[0]):
                stripes_flag = are_stripes_present(substack[k,:,:],reference)
                if stripes_flag:
                    stripe_frame_idx.append(frame_idx)
                frame_idx = frame_idx + 1
        self.stripe_frame_idx = np.array(stripe_frame_idx)
        
        #Find the intact frame that is closest to each striped frame
        if len(stripe_frame_idx) > 0:
            intact = np.array(set(np.arange(stack.shape[0])) - set(stripe_frame_idx))
            ref_idx = np.array([intact[np.argmin(np.abs(intact - x))] for x in stripe_frame_idx])
            self.ref_frame_idx = np.array(ref_idx)
        else:
            self.ref_frame_idx = np.array([])
        
        return
        
    def correct(self,key):
        '''Run the correction on the identified frames'''
        #The key is the labdata session to run it on. Keept this in for now so that you
        #run this on the session that is already downloaded and not automatically on all
        #sessions.
        
        if self.stripe_frame_idx.shape[0] > 0:
            stack = (Miniscope & key).open()

        #First create a binary file and write to the corrected frames to this one
        #Then use the compress imaging stack function to make the changed file
        
        '''
        z1 = compress_imaging_stack(data,
                                    compressed_file,
                                    chunksize = 512,
                                    compression = 'zstd',
                                    clevel = 6,
                                    shuffle = 1,
                                    filters = [])
        '''

        # this will create a zarr object the same size as the original
        # then:
            # go chunk by chunk # collect the frame indices changed
            # save the new file as you go by chunks
        return num_frames_changed,changed_frame_indices,filepath
    def make(self,key):
        num_frames_changed,changed_frame_indices,filepath = self.correct(key)
            # if no changes insert the table and move on. If there are changes:
            # replace the original file # danger
            # upload the new file to AWS: not destructive, keep versions. # this part needs testing
            # write to the table that the file was corrected
            #Avoid uploading the new .zip.zarr


key = ...Miniscope 1 session_name ).fetch("KEY")
MiniscopeStripeCorrection.populate(key)
#Remember that the populate method will call make, so no need to add this somewhere
#else
