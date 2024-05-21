import re
from xml.etree import ElementTree as ET

import requests
from shapely import Polygon


def fetch_geo_data():
    # URL and XML for first request (GetFeature)
    url = 'https://gsavalik.envir.ee/geoserver/wfs?service=WFS&version=1.1.0'
    area_query_xml = '''
        <GetFeature service="WFS" version="1.1.0"
            xmlns="http://www.opengis.net/wfs"
            xmlns:gml="http://www.opengis.net/gml"
            xmlns:ogc="http://www.opengis.net/ogc"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xsi:schemaLocation="http://www.opengis.net/wfs
            http://schemas.opengis.net/wfs/1.1.0/wfs.xsd">
            <Query typeName="metsaregister:eraldis">
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
            </Query>
        </GetFeature>
    '''

    headers = {
        'Content-Type': 'text/xml',
        'Accept': 'application/xml'
    }

    # Send first request
    response = requests.post(url, headers=headers, data=area_query_xml)
    if response.status_code != 200:
        print(f'Error in first request: {response.status_code}')
        return

    # Save response to file
    with open('forest_areas_response.xml', 'wb') as file:
        file.write(response.content)

    print("Response for first request saved to forest_areas_response.xml")

    # Parsing coordinates from first response
    xml_response = ET.fromstring(response.content)
    pos_list_elements = xml_response.findall(".//{http://www.opengis.net/gml}posList")

    if not pos_list_elements:
        print("posList elements not found in the response")
        return

    # Making list of polygons
    buffer_distance = -0.2  # 20cm buffer
    polygons = []
    for pos_list_element in pos_list_elements:
        pos_list = pos_list_element.text.strip().split()
        coordinates = [(float(pos_list[i]), float(pos_list[i + 1])) for i in range(0, len(pos_list), 2)]
        if len(coordinates) > 2:
            polygon = Polygon(coordinates).buffer(buffer_distance)
            polygons.append(polygon)

    print(f"Polygons found: {len(polygons)}")

    # Making conditions with Or operator for all polygons
    intersects_conditions = ""
    for polygon in polygons:
        pos_list = " ".join([f"{coord[0]} {coord[1]}" for coord in polygon.exterior.coords])
        intersects_conditions += f'''
                <ogc:Overlaps>
                    <ogc:PropertyName>shape</ogc:PropertyName>
                    <gml:Polygon>
                        <gml:exterior>
                            <gml:LinearRing>
                                <gml:posList>{pos_list}</gml:posList>
                            </gml:LinearRing>
                        </gml:exterior>
                    </gml:Polygon>
                </ogc:Overlaps>
                <ogc:Within>
                    <ogc:PropertyName>shape</ogc:PropertyName>
                    <gml:Polygon>
                        <gml:exterior>
                            <gml:LinearRing>
                                <gml:posList>{pos_list}</gml:posList>
                            </gml:LinearRing>
                        </gml:exterior>
                    </gml:Polygon>
                </ogc:Within>
                <ogc:Contains>
                    <ogc:PropertyName>shape</ogc:PropertyName>
                    <gml:Polygon>
                        <gml:exterior>
                            <gml:LinearRing>
                                <gml:posList>{pos_list}</gml:posList>
                            </gml:LinearRing>
                        </gml:exterior>
                    </gml:Polygon>
                </ogc:Contains>
            '''

    # XML for second request (GetFeature with filter)
    forest_query_xml = f'''
        <GetFeature service="WFS" version="1.1.0"
            xmlns="http://www.opengis.net/wfs"
            xmlns:gml="http://www.opengis.net/gml"
            xmlns:ogc="http://www.opengis.net/ogc"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xsi:schemaLocation="http://www.opengis.net/wfs
            http://schemas.opengis.net/wfs/1.1.0/wfs.xsd">
            <Query typeName="metsaregister:teatis">
                <ogc:Filter>
                    <ogc:Or>
                        {intersects_conditions}
                    </ogc:Or>
                </ogc:Filter>
            </Query>
        </GetFeature>
    '''

    # Saving second request XML to file
    with open('teatis_query.xml', 'w') as file:
        file.write(forest_query_xml)

    print("Second request saved to teatis_query.xml")

    # Sending second request for getting all relevant areas
    response = requests.post(url, headers=headers, data=forest_query_xml)
    if response.status_code != 200:
        print(f'Error in second request: {response.status_code}')
        return

    # Saving response to file
    with open('overlaps_within_contains_buffer_20cm.xml', 'wb') as file:
        file.write(response.content)

    print("Second response saved to overlaps_within_contains_buffer_20cm.xml")

    # Processing response for getting relevant areas
    xml_response = response.content.decode('utf-8')
    teatis_elements = re.findall(r'(<metsaregister:teatis .*?</metsaregister:teatis>)', xml_response, re.DOTALL)

    # Extract and count valid notifications
    valid_notifications_count = 0
    for teatis in teatis_elements:
        otsus_kinnitatud_kp = re.search(r'<metsaregister:otsus_kinnitatud_kp>(.*?)</metsaregister:otsus_kinnitatud_kp>',
                                        teatis)
        if otsus_kinnitatud_kp:
            valid_notifications_count += 1

    # Print the result
    print(f'Valid notifications count: {valid_notifications_count}')


if __name__ == "__main__":
    fetch_geo_data()
