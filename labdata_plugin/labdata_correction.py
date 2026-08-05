from labdata.schema import *

@get_user_schema()
class MiniscopeStripeCorrection(dj.Computed):
    definition = '''
    -> Miniscope
    ---
    num_frames_changed = 0       : int
    changed_frame_indices = NULL : longblob       # the frames that had to be corrected
    previous_checksum = NULL     : varchar(32)    # checksum of the processed file
    ''''
    def check_session(self,key):
        # this is for checking if data has artifacts and fixing it
        raise NotImplementedError('do it.')

    def correct(self,key):
        stack = (Miniscope & key).open()
#The key is the labdata session to run it on. Keept this in for now so that you
#run this on the session that is already downloaded and not automatically on all
#sessions.


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


key = ...Miniscope 1 session_name ).fetch("KEY")
MiniscopeStripeCorrection.populate(key)
#Remember that the populate method will call make, so no need to add this somewhere
#else
