import requests
from lxml import html
from pykml import parser
import gpxpy
import argparse


def get_region_passes_in_kml(lat1: float, lon1: float, lat2: float, lon2: float, host: str = 'https://westra.ru'):
    resp = requests.get(f'{host}/passes/kml/passes.php?BBOX={lon1},{lat1},{lon2},{lat2}')
    if resp.status_code == 200:
        root = parser.fromstring(resp.text.encode('utf-8'))
        return root


def passes_from_kml_to_gpx(kml):
    gpx_data = gpxpy.gpx.GPX()
    if kml.Document.Folder is not None:
        for folder in kml.Document.Folder:
            for placemark in folder.Placemark:
                # Create first track in our GPX:
                pass_waypoint = gpxpy.gpx.GPXWaypoint()

                # Get altitude from point description
                root = html.fromstring(str(placemark.description))
                altitude = root.xpath('//tr/th[contains(text(), "Высота")]//following-sibling::td/text()')[0]

                # Fill GPX point data
                pass_waypoint.name = f"{placemark.name} {str(folder.name)} {altitude}"
                pass_waypoint.latitude = placemark.LookAt.latitude
                pass_waypoint.longitude = placemark.LookAt.longitude
                pass_waypoint.elevation = float(int(altitude))

                gpx_data.waypoints.append(pass_waypoint)
    return gpx_data


def get_track_bounds_offset(gpx_track: str, offset_km: int):
    track_gpx = open_gpx(gpx_track)

    # Get track bounds
    (min_lat, max_lat, min_lon, max_lon) = track_gpx.get_bounds()

    offset_m = offset_km * 1000

    # Offset helpers
    offset_north = gpxpy.geo.LocationDelta(distance=offset_m, angle=0)
    offset_east = gpxpy.geo.LocationDelta(distance=offset_m, angle=90)
    offset_west = gpxpy.geo.LocationDelta(distance=offset_m, angle=270)
    offset_south = gpxpy.geo.LocationDelta(distance=offset_m, angle=180)

    # Bounds Offset
    waypointSW = gpxpy.gpx.GPXWaypoint()
    waypointSW.name = f"Extreme southeastern point"
    waypointSW.latitude = min_lat
    waypointSW.longitude = min_lon
    waypointSW.latitude, waypointSW.longitude = offset_south.move_by_angle_and_distance(waypointSW)
    waypointSW.latitude, waypointSW.longitude = offset_west.move_by_angle_and_distance(waypointSW)

    waypointNE = gpxpy.gpx.GPXWaypoint()
    waypointNE.name = f"Extreme northwestern point"
    waypointNE.latitude = max_lat
    waypointNE.longitude = max_lon
    waypointNE.latitude, waypointNE.longitude = offset_north.move_by_angle_and_distance(waypointNE)
    waypointNE.latitude, waypointNE.longitude = offset_east.move_by_angle_and_distance(waypointNE)

    return waypointSW.latitude, waypointSW.longitude, waypointNE.latitude, waypointNE.longitude


def save_gpx(filename, gpx):
    with open(filename, "w", encoding="utf-8") as file:
        file.write(gpx.to_xml())


def open_gpx(file_path):
    gpx_file = open(file_path, 'r', encoding="utf-8")
    gpx_data = gpxpy.parse(gpx_file)
    gpx_file.close()
    return gpx_data


def westra_passes_to_gpx(i, o, offset=5, host='https://westra.ru'):
    bounds = get_track_bounds_offset(i, offset)
    kml = get_region_passes_in_kml(*bounds, host=host)
    gpx = passes_from_kml_to_gpx(kml)
    save_gpx(o, gpx)


arg_parser = argparse.ArgumentParser(description='Allows you to download from the catalog of passes of the Westra tourist '
                                             'club the coordinates of the passes in the vicinity of the GPS track')

arg_parser.add_argument(
                    dest='i',
                    type=str,
                    help='path to input gpx track')
arg_parser.add_argument(
                    dest='o',
                    type=str,
                    help='path to output gpx')

arg_parser.add_argument('--offset',
                    dest='offset',
                    action='store',
                    default=5,
                    type=int,
                    help='Offset from track bounds for loading passes, in km')

arg_parser.add_argument('--host',
                    dest='host',
                    action='store',
                    default="https://westra.ru",
                    type=str,
                    help='Westra passes site adress. By default, "https://westra.ru"')

args = arg_parser.parse_args()
westra_passes_to_gpx(args.i, args.o, offset=args.offset, host=args.host)
