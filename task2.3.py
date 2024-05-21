import requests
import xml.etree.ElementTree as ET

def fetch_geo_data():
    # URL and XML for the GetFeature request
    url = 'https://gsavalik.envir.ee/geoserver/wfs?service=WFS&version=1.1.0'
    area_query_xml = '''
        <GetFeature service="WFS" version="1.1.0"
            xmlns="http://www.opengis.net/wfs"
            xmlns:gml="http://www.opengis.net/gml"
            xmlns:ogc="http://www.opengis.net/ogc"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xmlns:wfs="http://www.opengis.net/wfs"
            xsi:schemaLocation="http://www.opengis.net/wfs
            http://schemas.opengis.net/wfs/1.1.0/wfs.xsd">
            <wfs:Query typeName="metsaregister:eraldis" srsName="EPSG:3301">
                <wfs:PropertyName>metsaregister:pindala</wfs:PropertyName>
                <ogc:Filter>
                    <ogc:And>
                        <ogc:PropertyIsGreaterThanOrEqualTo>
                            <ogc:PropertyName>invent_kp</ogc:PropertyName>
                            <ogc:Literal>2023-01-01T00:00:00Z</ogc:Literal>
                        </ogc:PropertyIsGreaterThanOrEqualTo>
                        <ogc:PropertyIsLessThanOrEqualTo>
                            <ogc:PropertyName>invent_kp</ogc:PropertyName>
                            <ogc:Literal>2023-12-31T23:59:59Z</ogc:Literal>
                        </ogc:PropertyIsLessThanOrEqualTo>
                        <ogc:PropertyIsEqualTo>
                            <ogc:PropertyName>peapuuliik_kood</ogc:PropertyName>
                            <ogc:Literal>TA</ogc:Literal>
                        </ogc:PropertyIsEqualTo>
                    </ogc:And>
                </ogc:Filter>
            </wfs:Query>
        </GetFeature>
    '''

    headers = {
        'Content-Type': 'text/xml',
        'Accept': 'application/xml'
    }

    # Send the request
    response = requests.post(url, headers=headers, data=area_query_xml)
    if response.status_code != 200:
        print(f'Error in request: {response.status_code}')
        return

    # Save the response to a file
    with open('sum_response.xml', 'wb') as file:
        file.write(response.content)

    # Parse the XML response to sum up 'pindala' values
    tree = ET.fromstring(response.content)
    namespaces = {
        'gml': "http://www.opengis.net/gml",
        'metsaregister': "https://mets-ave.envir.ee"
    }

    # Find all 'pindala' elements
    pindala_elements = tree.findall('.//metsaregister:pindala', namespaces)
    print(f'Total elements: {len(pindala_elements)}')
    pindala_values = [float(pindala.text) for pindala in pindala_elements]

    # Calculate total and average 'pindala'
    total_pindala = sum(pindala_values)

    print(f'Total area: {total_pindala}')

if __name__ == "__main__":
    fetch_geo_data()
