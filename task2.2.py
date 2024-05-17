import requests
from xml.etree import ElementTree as ET
from shapely.geometry import Polygon
import json
import re

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
            <Query typeName="ehak:maakondade_piirid">
                <ogc:Filter>
                    <ogc:PropertyIsEqualTo>
                        <ogc:PropertyName>fid</ogc:PropertyName>
                        <ogc:Literal>7</ogc:Literal>
                    </ogc:PropertyIsEqualTo>
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
    with open('area_response.xml', 'wb') as file:
        file.write(response.content)

    print("Response for first request saved to area_response.xml")

    # Parsing coordinates from first response
    xml_response = ET.fromstring(response.content)
    pos_list_elements = xml_response.findall(".//{http://www.opengis.net/gml}posList")

    if not pos_list_elements:
        print("posList elements not found in the response")
        return

    # Making list of polygons
    polygons = []
    for pos_list_element in pos_list_elements:
        pos_list = pos_list_element.text.strip()
        polygons.append(pos_list)

    print(f"Polygons found: {len(polygons)}")

    # Making conditions with Or operator for all polygons
    intersects_conditions = ""
    for pos_list in polygons:
        intersects_conditions += f'''
            <ogc:Intersects>
                <ogc:PropertyName>shape</ogc:PropertyName>
                <gml:Polygon>
                    <gml:exterior>
                        <gml:LinearRing>
                            <gml:posList>{pos_list}</gml:posList>
                        </gml:LinearRing>
                    </gml:exterior>
                </gml:Polygon>
            </ogc:Intersects>
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
                        <ogc:Or>
                            {intersects_conditions}
                        </ogc:Or>
                    </ogc:And>
                </ogc:Filter>
            </Query>
        </GetFeature>
    '''

    # Saving second request XML to file
    with open('forest_query.xml', 'w') as file:
        file.write(forest_query_xml)

    print("Second request saved to forest_query.xml")

    # Sending second request for getting all forest areas
    response = requests.post(url, headers=headers, data=forest_query_xml)
    if response.status_code != 200:
        print(f'Error in second request: {response.status_code}')
        return

    # Saving response to file
    with open('forest_response.xml', 'wb') as file:
        file.write(response.content)

    print("Second response saved to forest_response.xml")

    # Processing response for getting forest areas and their centroids
    xml_response = response.content.decode('utf-8')
    eraldis_elements = re.findall(r'(<metsaregister:eraldis .*?</metsaregister:eraldis>)', xml_response, re.DOTALL)

    # Checking XML structure and printing amount of records
    feature_count = len(eraldis_elements)
    print('Feature members:', feature_count)

    # Centroids coordinates list
    centroids = []

    for eraldis_element in eraldis_elements:
        pos_list_elements = re.findall(r'<gml:posList>(.*?)</gml:posList>', eraldis_element, re.DOTALL)
        for pos_list_element in pos_list_elements:
            pos_list = pos_list_element.strip().split()
            coordinates = [(float(pos_list[i]), float(pos_list[i + 1])) for i in range(0, len(pos_list), 2)]
            if len(coordinates) > 2:  # We should make sure that there is at least 3 points to make polygon
                polygon = Polygon(coordinates)
                centroid = polygon.centroid
                centroids.append(centroid)
            else:
                print("Not enough coordinates to form a polygon:", coordinates)

    print('Centroids amount:', len(centroids))

    # Saving centroids to file for further analysis
    with open('centroids.json', 'w') as f:
        centroids_data = [{"x": centroid.x, "y": centroid.y} for centroid in centroids]
        json.dump(centroids_data, f, indent=4)

    print("Centroids saved to centroids.json")

    # Making request to check centroids intersects with maakond areas
    intersect_count = 0

    for centroid in centroids:
        intersection_query_xml = f'''
            <GetFeature service="WFS" version="1.1.0"
                xmlns="http://www.opengis.net/wfs"
                xmlns:gml="http://www.opengis.net/gml"
                xmlns:ogc="http://www.opengis.net/ogc"
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                xsi:schemaLocation="http://www.opengis.net/wfs
                http://schemas.opengis.net/wfs/1.1.0/wfs.xsd">
                <Query typeName="ehak:maakondade_piirid">
                    <PropertyName>fid</PropertyName>
                    <PropertyName>maakond</PropertyName>
                    <ogc:Filter>
                        <ogc:Intersects>
                            <ogc:PropertyName>shape</ogc:PropertyName>
                            <gml:Point srsName="urn:ogc:def:crs:EPSG::3301">
                                <gml:pos>{centroid.x} {centroid.y}</gml:pos>
                            </gml:Point>
                        </ogc:Intersects>
                    </ogc:Filter>
                </Query>
            </GetFeature>
            '''

        response = requests.post(url, headers=headers, data=intersection_query_xml)
        if response.status_code == 200:
            xml_response = response.content.decode('utf-8')
            matches = re.findall(r'<ehak:maakond>(.*?)</ehak:maakond>', xml_response)
            if matches and 'Lääne maakond':
                intersect_count += 1
                for match in matches:
                    print(f'Centroid {centroid.x}, {centroid.y} located in maakond: {match}')

    print(f'Amount of centroids that located in Lääne maakond: {intersect_count}')

if __name__ == "__main__":
    fetch_geo_data()
