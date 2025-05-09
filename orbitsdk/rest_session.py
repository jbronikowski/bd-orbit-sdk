import json
import random
import sys
import time
import urllib.parse
from datetime import datetime

import requests

from orbitsdk.__init__ import __version__
from orbitsdk.common import *
from orbitsdk.config import *


# Main module interface
class RestSession(object):
    def __init__(
        self,
        logger,
        api_key,
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
        simulate=SIMULATE_API_CALLS,
        use_iterator_for_get_pages=USE_ITERATOR_FOR_GET_PAGES,
    ):
        super(RestSession, self).__init__()

        # Initialize attributes and properties
        self._version = __version__
        self._api_key = str(api_key)
        self._base_url = str(base_url)
        self._single_request_timeout = single_request_timeout
        self._certificate_path = certificate_path
        self._requests_proxy = requests_proxy
        self._wait_on_rate_limit = wait_on_rate_limit
        self._nginx_429_retry_wait_time = nginx_429_retry_wait_time
        self._action_batch_retry_wait_time = action_batch_retry_wait_time
        self._network_delete_retry_wait_time = network_delete_retry_wait_time
        self._retry_4xx_error = retry_4xx_error
        self._retry_4xx_error_wait_time = retry_4xx_error_wait_time
        self._maximum_retries = maximum_retries
        self._simulate = simulate
        self.use_iterator_for_get_pages = use_iterator_for_get_pages

        # Initialize a new `requests` session
        self._req_session = requests.session()
        self._req_session.encoding = 'utf-8'

        check_python_version()

        # Check base URL
        if self._base_url[-1] == '/':
            self._base_url = self._base_url[:-1]

        # Update the headers for the session
        self._req_session.headers = {
            'Authorization': 'Bearer ' + self._api_key,
            'Content-Type': 'application/json'
        }

        # Log API calls
        self._logger = logger
        self._parameters = {'version': self._version}
        self._parameters.update(locals())
        self._parameters.pop('self')
        self._parameters.pop('logger')
        self._parameters.pop('__class__')
        self._parameters['api_key'] = '*' * 36 + self._api_key[-4:]
        if self._logger:
            self._logger.info(f'Orbit SDK API session initialized with these parameters: {self._parameters}')

    @property
    def use_iterator_for_get_pages(self):
        return self._use_iterator_for_get_pages

    @use_iterator_for_get_pages.setter
    def use_iterator_for_get_pages(self, value):
        if value:
            self.get_pages = self._get_pages_iterator
        else:
            self.get_pages = self._get_pages_legacy

        self._use_iterator_for_get_pages = value

    def request(self, metadata, method, url, **kwargs):
        # Metadata on endpoint
        tag = metadata['tags'][0]
        operation = metadata['operation']

        # Update request kwargs with session defaults
        if self._certificate_path:
            kwargs.setdefault('verify', self._certificate_path)
        if self._requests_proxy:
            kwargs.setdefault('proxies', {'https': self._requests_proxy})
        kwargs.setdefault('timeout', self._single_request_timeout)

        abs_url = self._base_url + url

        # Set maximum number of retries
        retries = self._maximum_retries

        # Option to simulate non-safe API calls without actually sending them
        if self._logger:
            self._logger.debug(metadata)
        if self._simulate and method != 'GET':
            if self._logger:
                self._logger.info(f'{tag}, {operation} - SIMULATED')
            return None
        else:
            response = None
            while retries > 0:
                # Make the HTTP request to the API endpoint
                try:
                    if response:
                        response.close()
                    if self._logger:
                        self._logger.info(f'{method} {abs_url}')
                    response = self._req_session.request(method, abs_url, allow_redirects=False,verify=False,
                                                         **kwargs)
                    reason = response.reason if response.reason else ''
                    status = response.status_code
                except requests.exceptions.RequestException as e:
                    if self._logger:
                        self._logger.warning(f'{tag}, {operation} - {e}, retrying in 1 second')
                    time.sleep(1)
                    retries -= 1
                    if retries == 0:
                        if e.response and e.response.status_code:
                            raise APIError(metadata, APIResponseError(e.__class__.__name__,
                                                                      e.response.status_code, str(e)))
                        else:
                            raise APIError(metadata, APIResponseError(e.__class__.__name__, 503, str(e)))
                    else:
                        continue
                if self._logger:
                    self._logger.debug(f'{tag}, {operation} - {status} {reason}')
                    self._logger.debug(f'{tag}, {operation} - {response.headers}')
                    self._logger.debug(f'{tag}, {operation} - {response.content}')

                # 2XX success
                if response.ok:
                    if 'page' in metadata:
                        counter = metadata['page']
                        if self._logger:
                            self._logger.info(f'{tag}, {operation}; page {counter} - {status} {reason}')
                    else:
                        if self._logger:
                            self._logger.info(f'{tag}, {operation} - {status} {reason}')
                    # For non-empty response to GET, ensure valid JSON
                    try:
                        if method == 'GET' and response.content.strip():
                            response.json()
                        return response
                    except json.decoder.JSONDecodeError as e:
                        if self._logger:
                            self._logger.warning(f'{tag}, {operation} - {e}, retrying in 1 second')
                        time.sleep(1)
                        retries -= 1
                        if retries == 0:
                            raise APIError(metadata, response)
                        else:
                            continue

                # Rate limit 429 errors
                elif status == 429:
                    if 'Retry-After' in response.headers:
                        wait = int(response.headers['Retry-After'])
                    else:
                        wait = random.randint(1, self._nginx_429_retry_wait_time)
                    if self._logger:
                        self._logger.warning(f'{tag}, {operation} - {status} {reason}, retrying in {wait} seconds')
                    time.sleep(wait)
                    retries -= 1
                    if retries == 0:
                        raise APIError(metadata, response)

                # 5XX errors
                elif status >= 500:
                    if self._logger:
                        self._logger.warning(f'{tag}, {operation} - {status} {reason}, retrying in 1 second')
                    time.sleep(1)
                    retries -= 1
                    if retries == 0:
                        raise APIError(metadata, response)

                # 4XX errors
                else:
                    try:
                        message = response.json()
                        message_is_dict = True
                    except ValueError:
                        message = response.content[:100]
                        message_is_dict = False

                    # Check for specific concurrency errors
                    network_delete_concurrency_error_text = 'This may be due to concurrent requests to delete networks.'
                    action_batch_concurrency_error = {'errors': [
                        'Too many concurrently executing batches. Maximum is 5 confirmed but not yet executed batches.']
                    }
                    # Check specifically for network delete concurrency error
                    if message_is_dict and 'errors' in message.keys() \
                            and network_delete_concurrency_error_text in message['errors'][0]:
                        wait = random.randint(30, self._network_delete_retry_wait_time)
                        if self._logger:
                            self._logger.warning(f'{tag}, {operation} - {status} {reason}, retrying in {wait} seconds')
                        time.sleep(wait)
                        retries -= 1
                        if retries == 0:
                            raise APIError(metadata, response)
                    # Check specifically for action batch concurrency error
                    elif message == action_batch_concurrency_error:
                        wait = self._action_batch_retry_wait_time
                        if self._logger:
                            self._logger.warning(f'{tag}, {operation} - {status} {reason}, retrying in {wait} seconds')
                        time.sleep(wait)
                        retries -= 1
                        if retries == 0:
                            raise APIError(metadata, response)
                    elif self._retry_4xx_error:
                        wait = random.randint(1, self._retry_4xx_error_wait_time)
                        if self._logger:
                            self._logger.warning(f'{tag}, {operation} - {status} {reason}, retrying in {wait} seconds')
                        time.sleep(wait)
                        retries -= 1
                        if retries == 0:
                            raise APIError(metadata, response)

                    # All other client-side errors
                    else:
                        if self._logger:
                            self._logger.error(f'{tag}, {operation} - {status} {reason}, {message}')
                        raise APIError(metadata, response)

    def get(self, metadata, url, params=None):
        metadata['method'] = 'GET'
        metadata['url'] = url
        metadata['params'] = params
        response = self.request(metadata, 'GET', url, params=params)
        ret = None
        if response:
            if response.content.strip():
                ret = response.json()
            response.close()
        return ret

    def get_pages(self, metadata, url, params=None, total_pages=-1, direction='next', event_log_end_time=None):
        pass

    def _get_pages_iterator(
        self,
        metadata,
        url,
        params=None,
        total_pages=-1,
        direction="next",
        event_log_end_time=None,
    ):
        if type(total_pages) == str and total_pages.lower() == "all":
            total_pages = -1
        elif type(total_pages) == str and total_pages.isnumeric():
            total_pages = int(total_pages)
        metadata["page"] = 1

        response = self.request(metadata, 'GET', url, params=params)

        # Get additional pages if more than one requested
        while total_pages != 0:
            results = response.json()
            links = response.links

            # GET the subsequent page
            if direction == "next" and "next" in links:
                # Prevent getNetworkEvents from infinite loop as time goes forward
                if metadata["operation"] == "getNetworkEvents":
                    starting_after = urllib.parse.unquote(
                        str(links["next"]["url"]).split("startingAfter=")[1]
                    )
                    delta = datetime.utcnow() - datetime.fromisoformat(
                        starting_after[:-1]
                    )
                    # Break out of loop if startingAfter returned from next link is within 5 minutes of current time
                    if delta.total_seconds() < 300:
                        break
                    # Or if next page is past the specified window's end time
                    elif event_log_end_time and starting_after > event_log_end_time:
                        break

                metadata["page"] += 1
                nextlink = links["next"]["url"]
            elif direction == "prev" and "prev" in links:
                # Prevent getNetworkEvents from infinite loop as time goes backward (to epoch 0)
                if metadata["operation"] == "getNetworkEvents":
                    ending_before = urllib.parse.unquote(
                        str(links["prev"]["url"]).split("endingBefore=")[1]
                    )
                    # Break out of loop if endingBefore returned from prev link is before 2014
                    if ending_before < "2014-01-01":
                        break

                metadata["page"] += 1
                nextlink = links["prev"]["url"]
            else:
                break

            response.close()

            return_items = []
            # just prepare the list
            if type(results) == list:
                return_items = results
            # For event log endpoint
            elif type(results) == dict:
                if direction == "next":
                    return_items = results["events"][::-1]
                else:
                    return_items = results["events"]

            for item in return_items:
                yield item

            total_pages = total_pages - 1

            if total_pages != 0:
                response = self.request(metadata, 'GET', nextlink)

    def _get_pages_legacy(self, metadata, url, params=None, total_pages=-1, direction='next', event_log_end_time=None):
        if type(total_pages) == str and total_pages.lower() == 'all':
            total_pages = -1
        elif type(total_pages) == str and total_pages.isnumeric():
            total_pages = int(total_pages)
        metadata['page'] = 1

        response = self.request(metadata, 'GET', url, params=params)

        # Handle GETs that produce 204 No Content responses, e.g. getOrganizationClientSearch
        if response.status_code == 204:
            results = None
        else:
            results = response.json()

        # For event log endpoint when using 'next' direction, so results/events are sorted chronologically
        if type(results) == dict and metadata['operation'] == 'getNetworkEvents' and direction == 'next':
            results['events'] = results['events'][::-1]

        # Get additional pages if more than one requested
        while total_pages != 1:
            links = response.links
            response.close()
            response = None

            # GET the subsequent page
            if direction == 'next' and 'next' in links:
                # Prevent getNetworkEvents from infinite loop as time goes forward
                if metadata['operation'] == 'getNetworkEvents':
                    starting_after = urllib.parse.unquote(links['next']['url'].split('startingAfter=')[1])
                    delta = datetime.utcnow() - datetime.fromisoformat(starting_after[:-1])
                    # Break out of loop if startingAfter returned from next link is within 5 minutes of current time
                    if delta.total_seconds() < 300:
                        break
                    # Or if next page is past the specified window's end time
                    elif event_log_end_time and starting_after > event_log_end_time:
                        break

                metadata['page'] += 1
                response = self.request(metadata, 'GET', links['next']['url'])
            elif direction == 'prev' and 'prev' in links:
                # Prevent getNetworkEvents from infinite loop as time goes backward (to epoch 0)
                if metadata['operation'] == 'getNetworkEvents':
                    ending_before = urllib.parse.unquote(links['prev']['url'].split('endingBefore=')[1])
                    # Break out of loop if endingBefore returned from prev link is before 2014
                    if ending_before < '2014-01-01':
                        break

                metadata['page'] += 1
                response = self.request(metadata, 'GET', links['prev']['url'])
            else:
                break

            # Append that page's results, depending on the endpoint
            if isinstance(results, list):
                results.extend(response.json())
            # For event log endpoint
            elif isinstance(results, dict):
                try:
                    start = response.json()['pageStartAt']
                except KeyError:
                    print(response.headers)
                end = response.json()['pageEndAt']
                events = response.json()['events']
                if direction == 'next':
                    events = events[::-1]
                if start < results['pageStartAt']:
                    results['pageStartAt'] = start
                if end > results['pageEndAt']:
                    results['pageEndAt'] = end
                results['events'].extend(events)

            total_pages -= 1

        if response:
            response.close()

        return results

    def post(self, metadata, url, json=None):
        metadata['method'] = 'POST'
        metadata['url'] = url
        metadata['json'] = json
        response = self.request(metadata, 'POST', url, json=json)
        ret = None
        if response:
            if response.content.strip():
                ret = response.json()
            response.close()
        return ret

    def put(self, metadata, url, json=None):
        metadata['method'] = 'PUT'
        metadata['url'] = url
        metadata['json'] = json
        response = self.request(metadata, 'PUT', url, json=json)
        ret = None
        if response:
            if response.content.strip():
                ret = response.json()
            response.close()
        return ret

    def delete(self, metadata, url):
        metadata['method'] = 'DELETE'
        metadata['url'] = url
        response = self.request(metadata, 'DELETE', url)
        if response:
            response.close()
        return None
