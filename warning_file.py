import io

class WarningFile:
    def __init__(self, file_path, append=False):
        self.file_path = file_path
        if append:
            self.file = open(file_path, 'a')

        else:
            self.file = open(file_path, 'w')

    def write(self, message):
        self.file.write(message)
        self.file.write('\n')
        self.file.flush()
        
    def close(self):    
        self.file.close()

    def __del__(self):
        self.close()