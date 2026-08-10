from labdata.schema import *
import labdata
import labdata.rules

schema = get_user_schema()

@schema
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
            intact = list(set(np.arange(stack.shape[0])) - set(stripe_frame_idx))
            ref_idx = np.array([intact[np.argmin(np.abs(np.array(intact) - x))] for x in stripe_frame_idx])
            self.ref_frame_idx = np.array(ref_idx)
        else:
            self.ref_frame_idx = np.array([])
        
        return
        
    def correct(self,key):
        '''Run the correction on the identified frames'''
        
        if self.stripe_frame_idx.shape[0] > 0:
            stack = (Miniscope & key).open()
            
            #First, write an uncompressed binary file
            df = pd.DataFrame(Miniscope & key)
            corrected_file_name = os.path.join(os.path.split(labdata.find_local_filepath(df['file_path'][0]))[0], 'miniscope_stack_corrected.bin')
            
            out = np.memmap(corrected_file_name,mode = 'w+',dtype = stack.dtype,shape=stack.shape)
            out.flush()
            for o,f in tqdm(chunk_indices(stack.shape[0])):
                out[o:f,:,:] = stack[o:f,:,:]
                assert np.all(out[o:f] == stack[o:f]),ValueError('bo')
           
 
            self.correction_quality = np.zeros([self.stripe_frame_idx.shape[0]]) *np.nan
            for k in tqdm(range(self.stripe_frame_idx.shape[0])):
                full_stripe_indices, buffers = find_buffer_indices(out[self.stripe_frame_idx[k],:,:],
                                                                   out[self.ref_frame_idx[k],:,:])
                reconstructed_frame, self.correction_quality[k] = shift_stripes(out[self.stripe_frame_idx[k],:,:],
                                                             out[self.ref_frame_idx[k],:,:],
                                                             full_stripe_indices, buffers)
                out[self.stripe_frame_idx[k],:,:] = reconstructed_frame
                
            compressed_file_name = os.path.splitext(corrected_file_name)[0] + '.zarr.zip'
            z1 = labdata.rules.compress_imaging_stack(out,
                                    compressed_file_name,
                                    chunksize = 512,
                                    compression = 'zstd',
                                    clevel = 6,
                                    shuffle = 1,
                                    filters = [])
            
            #Remove the large binary file
            os.remove(corrected_file_name)
        
            num_frames_changed = self.stripe_frame_idx.shape[0]
            changed_frame_indices = self.stripe_frame_idx
            filepath = compressed_file_name
            
        else:
            num_frames_changed = 0
            changed_frame_indices = None
            filepath = None
            
        previous_filepath = labdata.find_local_filepath(pd.DataFrame((Miniscope & key))['file_path'][0])
            
        return num_frames_changed,changed_frame_indices,filepath, previous_filepath
    
    
    def make(self,key):
        '''Run the correction on the specified session'''
        
        #Find frames with the stripe artifact      
        self.check_session(key)
        
        #Correct these frames
        num_frames_changed,changed_frame_indices,filepath, previous_filepath = self.correct(key)
        
        #Compute checksums on previous and current file
        if filepath is not None:
            checksums = labdata.compute_md5s([previous_filepath, filepath], n_jobs=8, show_progress=False, suppress_file_not_found=False)
        else:
            checksums = labdata.compute_md5s([previous_filepath], n_jobs=8, show_progress=False, suppress_file_not_found=False)
        
        stripe_corr = {'num_frames_corrected': num_frames_corrected, 'changed_frame_indices': changed_frame_indices, 'previous_checksum': checksums[0]}
        
        self.insert1(key,**stripe_corr) #Here the key is still the animal id, session, etc. key

            # if no changes insert the table and move on. If there are changes:
            # replace the original file # danger
            # upload the new file to AWS: not destructive, keep versions. # this part needs testing
            # write to the table that the file was corrected
            #Avoid uploading the new .zip.zarr


# key = ...Miniscope 1 session_name ).fetch("KEY")
# MiniscopeStripeCorrection.populate(key)
# #Remember that the populate method will call make, so no need to add this somewhere
# #else
