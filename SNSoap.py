import requests
import zeep

class SNSoap:
    """Holds ServiceNow connection information for SOAP web service
    calls, and provides the run_query generator to simplify reading
    getRecords response.
    
    The authenticating user needs at least soap_query access (see
    ServiceNow base system role doc).

    sn = SNSoap(instance, username, password)
    for page in sn.run_query(table, query_parms):
        pass  # Process page_size records here,
              # (e.g. bulk-add records to a dataframe)
        for record in page:
            pass  # or perform individual record processing here

    For more on Zeep and ServiceNow, check out
    https://servicenowsoap.wordpress.com/2017/08/23/zeep-for-soap-web-services-from-python/
    """    
    def __init__(self, instance, username, password):
        self.instance = instance
        self.session = requests.Session()
        self.session.auth = requests.auth.HTTPBasicAuth(username, password)
        self.transport = zeep.transports.Transport(session=self.session)

    def _client(self, tablename):
        wsdl_url = 'https://%s.service-now.com/%s.do?WSDL' % (self.instance,
                                                              tablename)
        # Or use zeep.Client to skip SqliteCache of WSDL
        return zeep.CachingClient(wsdl_url, transport=self.transport)

    def run_query(self, table, query_parms=None, sys_ids=None, page_size=250):
        """Generator to wrap typical ServiceNow SOAP query flow of:
           bind service to client -> getKeys -> getRecords (with paging
           for large SOAP responses) -> process each page of responses

        This function calls getRecords with a specified list of
        desired sys_ids for a ServiceNow table.  It yields the
        getRecords responses, returned as a list of up to page_size
        zeep.objects.getRecordsResult objects.

        If sys_ids is not provided by the caller, this function will
        build a list of sys_ids by calling getKeys with query_parms,
        before following with the getRecords call.  Query_parms should
        be a dictionary of the arguments for the SOAP query,
        e.g. {'active':'false', 'state':7}.  Encoded queries are set
        like: {'__encoded_query':'active=false^state=7'}
        
        Being able to specify sys_ids is a convenience that is useful
        when making multiple calls to perform ad-hoc joins on tables
        for analytics (especially if you have no relevant database view
        defined in ServiceNow).

        The generator yields lists of zeep.objects.getRecordsResult
        objects. Usually you will simply treat each record as its
        own dictionary-like object with __getitem__, or an iterable.
        
        If you do want to convert a zeep.objects.getRecordsResult
        object into a native Python type (i.e. an ordered dict), use
        zeep.helpers.serialize_object(record).
        """
        page_size = int(page_size)
        assert(1 <= page_size <= 250)
        client = self._client(table)

        if sys_ids is None:
            # There were no sys_ids provided, so run a getKeys with
            # query_parms to retrieve a list of matching sys_ids
            response = client.service.getKeys(**query_parms)
            if int(response['count']) == 0:
                sys_ids = []
            else:
                sys_ids = response['sys_id'][0].split(',')
        else:
            # Remove duplicate sys_ids and None from user-provided sys_ids
            sys_ids = set(sys_ids)
            try:
                sys_ids.remove(None)
            except KeyError:
                pass
            sys_ids = list(sys_ids)

        # Page through getRecords, page_size sys_ids at a time
        start = 0
        while start < len(sys_ids):
            chunk = sys_ids[start: start + page_size]
            query = 'sys_idIN' + ','.join(chunk)
            yield client.service.getRecords(__encoded_query=query)
            start += page_size
