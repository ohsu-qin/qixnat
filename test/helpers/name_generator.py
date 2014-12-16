from base64 import b64encode as encode


def generate_unique_name(name):
    """
    Makes a name that is unique to the given test name.
    
    :param name: the test name
    :return: the test subject name
    """
    return encode(name).strip('=')
