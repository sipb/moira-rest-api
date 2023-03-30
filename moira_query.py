import moira
import concurrent.futures

# TODO: make this changeable by API clients?
CLIENT_NAME = 'python3'

def _moira_query(*args, **kwargs):
    """
    Runs the given Moira query, taking care to do all necessary 
    initialization and de-initialization
    """
    moira.connect()
    moira.auth(CLIENT_NAME)
    result = moira.query(*args, **kwargs)
    moira.disconnect()
    return result


def moira_query(*args, **kwargs):
    """
    Runs the given Moira query in a new process, so that
    environment variable changes (KRB5CCNAME) are actually honored
    """
    # https://stackoverflow.com/a/72490867/5031798
    with concurrent.futures.ProcessPoolExecutor() as executor:
        f = executor.submit(_moira_query, *args, **kwargs)
        ret = f.result()
    return ret
