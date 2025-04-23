import logging
import os

from orbitsdk.api.robots import Robots

# Config import
from orbitsdk.config import (
    API_KEY_ENVIRONMENT_VARIABLE,
    DEFAULT_BASE_URL,
    SINGLE_REQUEST_TIMEOUT,
    CERTIFICATE_PATH,
    REQUESTS_PROXY,
    WAIT_ON_RATE_LIMIT,
    NGINX_429_RETRY_WAIT_TIME,
    ACTION_BATCH_RETRY_WAIT_TIME,
    NETWORK_DELETE_RETRY_WAIT_TIME,
    RETRY_4XX_ERROR,
    RETRY_4XX_ERROR_WAIT_TIME,
    MAXIMUM_RETRIES,
    OUTPUT_LOG,
    LOG_PATH,
    LOG_FILE_PREFIX,
    PRINT_TO_CONSOLE,
    SUPPRESS_LOGGING,
    INHERIT_LOGGING_CONFIG,
    SIMULATE_API_CALLS,
    USE_ITERATOR_FOR_GET_PAGES,
)
from orbitsdk.rest_session import *

__version__ = '1.48.0'


class OrbitAPI(object):
    """
    **Creates a persistent Orbit dashboard API session**

    - api_key (string): API key generated in dashboard; can also be set as an environment variable Orbit_DASHBOARD_API_KEY
    - base_url (string): preceding all endpoint resources
    - single_request_timeout (integer): maximum number of seconds for each API call
    - certificate_path (string): path for TLS/SSL certificate verification if behind local proxy
    - requests_proxy (string): proxy server and port, if needed, for HTTPS
    - wait_on_rate_limit (boolean): retry if 429 rate limit error encountered?
    - nginx_429_retry_wait_time (integer): Nginx 429 retry wait time
    - action_batch_retry_wait_time (integer): action batch concurrency error retry wait time
    - network_delete_retry_wait_time (integer): network deletion concurrency error retry wait time
    - retry_4xx_error (boolean): retry if encountering other 4XX error (besides 429)?
    - retry_4xx_error_wait_time (integer): other 4XX error retry wait time
    - maximum_retries (integer): retry up to this many times when encountering 429s or other server-side errors
    - output_log (boolean): create an output log file?
    - log_path (string): path to output log; by default, working directory of script if not specified
    - log_file_prefix (string): log file name appended with date and timestamp
    - print_console (boolean): print logging output to console?
    - suppress_logging (boolean): disable all logging? you're on your own then!
    - inherit_logging_config (boolean): Inherits your own logger instance
    - simulate (boolean): simulate POST/PUT/DELETE calls to prevent changes?
    - be_geo_id (string): optional partner identifier for API usage tracking; can also be set as an environment variable BE_GEO_ID
    - caller (string): optional identifier for API usage tracking; can also be set as an environment variable Orbit_PYTHON_SDK_CALLER
    - use_iterator_for_get_pages (boolean): list* methods will return an iterator with each object instead of a complete list with all items
    """

    def __init__(self,
                 api_key=None,
                 base_url=DEFAULT_BASE_URL,
                 single_request_timeout=SINGLE_REQUEST_TIMEOUT,
                 certificate_path=CERTIFICATE_PATH,
                 requests_proxy=REQUESTS_PROXY,
                 wait_on_rate_limit=WAIT_ON_RATE_LIMIT,
                 nginx_429_retry_wait_time=NGINX_429_RETRY_WAIT_TIME,
                 action_batch_retry_wait_time=ACTION_BATCH_RETRY_WAIT_TIME,
                 network_delete_retry_wait_time=NETWORK_DELETE_RETRY_WAIT_TIME,
                 retry_4xx_error=RETRY_4XX_ERROR,
                 retry_4xx_error_wait_time=RETRY_4XX_ERROR_WAIT_TIME,
                 maximum_retries=MAXIMUM_RETRIES,
                 output_log=OUTPUT_LOG,
                 log_path=LOG_PATH,
                 log_file_prefix=LOG_FILE_PREFIX,
                 print_console=PRINT_TO_CONSOLE,
                 suppress_logging=SUPPRESS_LOGGING,
                 simulate=SIMULATE_API_CALLS,
                 use_iterator_for_get_pages=USE_ITERATOR_FOR_GET_PAGES,
                 inherit_logging_config=INHERIT_LOGGING_CONFIG,
                 ):

        # Check API key
        api_key = api_key or os.environ.get(API_KEY_ENVIRONMENT_VARIABLE)
        if not api_key:
            raise APIKeyError()


        use_iterator_for_get_pages = use_iterator_for_get_pages
        inherit_logging_config = inherit_logging_config

        # Configure logging
        if not suppress_logging:
            self._logger = logging.getLogger(__name__)

            if not inherit_logging_config:
                self._logger.setLevel(logging.DEBUG)

                formatter = logging.Formatter(
                    fmt='%(asctime)s %(name)12s: %(levelname)8s > %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                handler_console = logging.StreamHandler()
                handler_console.setFormatter(formatter)

                if output_log:
                    if log_path and log_path[-1] != '/':
                        log_path += '/'
                    self._log_file = f'{log_path}{log_file_prefix}_log__{datetime.now():%Y-%m-%d_%H-%M-%S}.log'
                    handler_log = logging.FileHandler(
                        filename=self._log_file
                    )
                    handler_log.setFormatter(formatter)

                if output_log and not self._logger.hasHandlers():
                    self._logger.addHandler(handler_log)
                    if print_console:
                        handler_console.setLevel(logging.INFO)
                        self._logger.addHandler(handler_console)
                elif print_console and not self._logger.hasHandlers():
                    self._logger.addHandler(handler_console)
        else:
            self._logger = None

        # Creates the API session
        self._session = RestSession(
            logger=self._logger,
            api_key=api_key,
            base_url=base_url,
            single_request_timeout=single_request_timeout,
            certificate_path=certificate_path,
            requests_proxy=requests_proxy,
            wait_on_rate_limit=wait_on_rate_limit,
            nginx_429_retry_wait_time=nginx_429_retry_wait_time,
            action_batch_retry_wait_time=action_batch_retry_wait_time,
            network_delete_retry_wait_time=network_delete_retry_wait_time,
            retry_4xx_error=retry_4xx_error,
            retry_4xx_error_wait_time=retry_4xx_error_wait_time,
            maximum_retries=maximum_retries,
            simulate=simulate,
            use_iterator_for_get_pages=use_iterator_for_get_pages,
        )

        # API endpoints by section
        self.robots = Robots(self._session)