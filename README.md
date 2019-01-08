# SNSoap

***
## Overview

The SNSoap module demonstrates a method for querying ServiceNow tables via ServiceNow's [SOAP web service](https://docs.servicenow.com/bundle/london-application-development/page/integrate/inbound-soap/concept/c_SOAPWebService.html).  It simplifies ad-hoc joins and queries for analytics against your ServiceNow environment in idiomatic python, without worrying about whatever plumbing lies between constructed query parameters and being able to iterate through the pages of results.

The **run_query()** generator abstracts away the typical ServiceNow flow of:

> bind service to client &rarr; [getKeys](https://docs.servicenow.com/integrate/web_services_apis/reference/r_GetKeys.html) &rarr; [getRecords](https://docs.servicenow.com/integrate/web_services_apis/reference/r_GetRecords.html) (with paging for large SOAP responses) &rarr; process each page of responses.

Once authenticated, you call the **run_query()** generator function with a *table* name and *query_parms*, then iterate over the pages of records in the response.  You can also make subsequent **run_query()** calls with specific *sys_ids* for related tables, which is useful for performing ad-hoc joins (especially if you don't already have a relevant database view defined in ServiceNow).

The authenticated ServiceNow user requires at least *soap_query* access in the target environment (see ServiceNow [Base System Roles](https://docs.servicenow.com/bundle/london-platform-administration/page/administer/roles/reference/r_BaseSystemRoles.html) doc).


***
## Parameters for run_query()

Create the **SNSoap** instance with:
```python
import SNSoap
sn = SNSoap.SNSoap(tenant, username, password)
```

The SNSoap instance contains the **run_query()** function with the following parameter list:
```python
run_query(table, query_parms=None, sys_ids=None, page_size=250)
```

### table
A string name for the targeted ServiceNow resource, such as those listed at [Tables and Classes](https://docs.servicenow.com/bundle/london-platform-administration/page/administer/reference-pages/reference/r_TablesAndClasses.html)

### query_parms
A dictionary of key/value pairs for the soap query, used when *sys_ids* is *None*

For example:
```python
{'active':'false', 'state':7}
```
[Encoded Query Strings](https://docs.servicenow.com/bundle/london-platform-user-interface/page/use/using-lists/concept/c_EncodedQueryStrings.html) are specified with a key of *__encoded_query*:
```python
{'__encoded_query':'mi_valueSTARTSWITHfoo^ORmi_value=bar'}
```

### sys_ids
An unordered list of primary keys for [getRecords](https://docs.servicenow.com/integrate/web_services_apis/reference/r_GetRecords.html) (technically, any iterable of objects supporting *\_\_str\_\_*)

Normally you are only providing *sys_ids* on subsequent calls, using keys found in reference fields from earlier queries of related tables.  Duplicate *sys_ids* are eliminated and order is not preserved in the response.  Each record in the response is uniquely identifiable by its key in the *sys_id* field.

### page_size
An integer specifying *sys_ids* chunk size

Requests that [retrieve a large number of records using SOAP](https://docs.servicenow.com/bundle/jakarta-application-development/page/integrate/examples/concept/c_RtvLrgNmbrRcrdSOAP.html?title=Retrieving_A_Large_Number_Of_Records_Using_SOAP) must be split into smaller queries, or risk an incomplete records result.  **run_query()** repeatedly yields responses as a list of up to *page_size* [zeep.objects.getRecordsResult](#zeep) objects, until no records remain.  ServiceNow currently limits SOAP responses to 250 records, but with paging it's no problem to pull down thousands, processed a page at a time.

Of course you can simply iterate over each record individually with a nested for loop to perform more complex evaluations and functions, rather than bulk-add records to your dataframe an entire page at a time.
```python
    for page in sn.run_query(table, query_parms):  # This blocks while the next page is downloaded
       for record in page:
           pass   # Process the response one record at a time here
```

***
## Zeep

SNSoap has a dependency on the [Zeep](https://python-zeep.readthedocs.io/en/master/) Python SOAP client library.  For more examples using the Zeep client with ServiceNow, check out [Zeep for Soap Web Services from Python](https://servicenowsoap.wordpress.com/2017/08/23/zeep-for-soap-web-services-from-python/).

SNSoap's **run_query()** generator yields lists of *zeep.objects.getRecordsResult* objects.  Usually you will simply treat each record as its own dictionary-like object with *\_\_getitem\_\_* (or iterable with *\_\_next\_\_*).

  * To convert the entire *zeep.objects.getRecordsResult* object into a native Python type (i.e. an ordered dict):
    ```python
    zeep.helpers.serialize_object(record)
    ```

  * To convert the yielded list of records into a list of dictionaries, capturing only fields of interest:
    ```python
    [{key: record[key] for key in desired_fields} for record in page]
    ```

***
## Quick Start

### Install

1. Install _Zeep_ and its dependencies (via [pip](https://pypi.org/project/pip/) recommended).
    ```shell
    pip install zeep
    ```

2. Add the SNSoap.py module into your directory for import

### Sample code

```python
import getpass
import SNSoap

tenant = 'mytenant'
username = 'myusername'
query = '^opened_at>=2018-01-01 00:00:00^opened_at<=2018-01-01 23:59:59'
password = getpass.getpass('Provide password for {}@{}:'.format(username, tenant))

sn = SNSoap.SNSoap(tenant, username, password)
request_items = {}   # We pre-initialize the dictionaries to append possibly
catalog_items = {}   # multi-page responses via one or more dictionary updates

for page in sn.run_query(table='sc_req_item_list', query_parms={'__encoded_query': query}):
    request_items.update({record['number']:record['cat_item'] for record in page})
for page in sn.run_query(table='sc_cat_item', sys_ids=request_items.values()):
    for record in page:   # Example processing one record at a time
        catalog_items[record['sys_id']] = record['name']
for request, cat_item in request_items.items():
    print('{} is a "{}" request'.format(request, catalog_items[cat_item]))
```

***
## License

The SNSoap module is released under the [MIT License](https://opensource.org/licenses/MIT)
