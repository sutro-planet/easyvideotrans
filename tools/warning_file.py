import io
import copy

class WarningFile:
    def __init__(self, file_path, append=False):
        self.file_path = file_path
        if append:
            self.file = open(file_path, 'a')

        else:
            self.file = open(file_path, 'w')

    def write(self, message, printMessage=True):
        self.file.write(message)
        self.file.write('\n')
        if printMessage:
            print(message)
        self.file.flush()
        
    def close(self):    
        self.file.close()

    def __del__(self):
        self.close()