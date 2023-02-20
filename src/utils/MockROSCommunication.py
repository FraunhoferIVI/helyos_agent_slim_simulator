import pickle, os
class MockROSCommunication():
    """ Disk-based mechanism to exchange data between threads"""
    __file = None
       
    def __init__(self, topic_name):
        try: 
            os.mkdir('tmp') 
        except OSError as error: 
            pass
        self.topic_name = f"./tmp/{topic_name}"
        self.__file = open(topic_name, 'wb')
        pickle.dump(None, self.__file)
        self.__file.close()
        
    def read(self):
        with open(self.topic_name, 'rb') as f:
            dictionary = pickle.load(f)
        return dictionary
    
    def pop(self):
        dictionary = self.read()
        self.publish(None)
        return dictionary
        
    def publish(self, dictionary):
        self.__file = open(self.topic_name, 'wb')
        pickle.dump(dictionary, self.__file)
        self.__file.close()