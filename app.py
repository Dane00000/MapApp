from flask import Flask, jsonify, request
import requests
from geopy.distance import geodesic

app = Flask(__name__)

# Google API key for Places, Geocoding, and Weather
API_KEY = 'AIzaSyAU4s250kiu-pxFzYNLgKTKOOZbnQ8pqMg'
WEATHER_API_KEY = '2c3955f87145defdb14d293b8ccda6f8'
BASE_WEATHER_URL = 'http://api.openweathermap.org/data/2.5/weather'
PLACES_URL = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json'
GEOCODING_URL = 'https://maps.googleapis.com/maps/api/geocode/json'

# List of cities with their latitudes and longitudes
cities = {
    'New York': (40.7128, -74.0060),
    'Los Angeles': (34.0522, -118.2437),
    'London': (51.5074, -0.1278),
    'Paris': (48.8566, 2.3522),
    'Tokyo': (35.6762, 139.6503)
}


def find_nearby_cities(click_lat, click_lng, radius_km=100):
    clicked_location = (click_lat, click_lng)
    nearby_cities = []

    for city, coords in cities.items():
        distance = geodesic(clicked_location, coords).km
        if distance <= radius_km:
            nearby_cities.append({'city': city, 'distance': distance, 'lat': coords[0], 'lng': coords[1]})

    return nearby_cities


def get_city_name_by_latlng(lat, lng):
    params = {
        'latlng': f'{lat},{lng}',
        'key': API_KEY
    }

    response = requests.get(GEOCODING_URL, params=params)
    data = response.json()

    if 'results' in data and len(data['results']) > 0:
        for result in data['results']:
            for component in result['address_components']:
                if 'locality' in component['types']:
                    return component['long_name']

    return "City not found"


@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Weather and Places Map</title>
        <style>
            #map {
                height: 620px;
                width: 100%;
            }
        </style>
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <script src="https://maps.googleapis.com/maps/api/js?key=AIzaSyAU4s250kiu-pxFzYNLgKTKOOZbnQ8pqMg&callback=initMap&libraries=places" async defer></script>
    </head>
    <body>
        <h1>Weather, City Info, and Places Map</h1>
        <input type="text" id="placeType" placeholder="Enter place type (e.g., market)">
        <button id="searchPlaces">Search Places</button>
        <div id="map"></div>

        <script>
            let map;

            function initMap() {
                map = new google.maps.Map(document.getElementById('map'), {
                    zoom: 2,
                    center: { lat: 0, lng: 0 }
                });
                map.addListener('click', function(event) {
                    const lat = event.latLng.lat();
                    const lng = event.latLng.lng();
                    getWeatherData(lat, lng);
                    getNearbyCities(lat, lng);
                    guessCityName(lat, lng);
                    searchNearbyPlaces(lat, lng);
                });
            }

            function getWeatherData(lat, lng) {
                $.get(`/weather_by_coordinates?lat=${lat}&lng=${lng}`, function(data) {
                    const { temperature, humidity, description, coordinates } = data;
                    const latLng = { lat: coordinates.lat, lng: coordinates.lon };

                    new google.maps.Marker({
                        position: latLng,
                        map: map,
                        title: `Weather: ${temperature}°C, ${humidity}%, ${description}`
                    });

                    map.setCenter(latLng);
                    alert(`Weather: ${temperature}°C, ${humidity}%, ${description}`);
                }).fail(function() {
                    alert('Weather data not available');
                });
            }

            function getNearbyCities(lat, lng) {
                $.get(`/nearby_cities?lat=${lat}&lng=${lng}`, function(data) {
                    data.forEach(function(city) {
                        const cityLatLng = { lat: city.lat, lng: city.lng };
                        new google.maps.Marker({
                            position: cityLatLng,
                            map: map,
                            title: `${city.city}: ${city.distance.toFixed(2)} km away`
                        });
                    });
                }).fail(function() {
                });
            }

            function guessCityName(lat, lng) {
                $.get(`/guess_city_name?lat=${lat}&lng=${lng}`, function(data) {
                    alert(`You clicked near ${data.city}`);
                }).fail(function() {
                    alert('City name could not be guessed');
                });
            }

            function searchNearbyPlaces(lat, lng) {
                const placeType = document.getElementById('placeType').value;
                if (!placeType) {
                    alert('Please enter a place type (e.g., market)');
                    return;
                }

                $.get(`/search_places?lat=${lat}&lng=${lng}&placeType=${placeType}`, function(data) {
                    data.places.forEach(function(place) {
                        const placeLatLng = { lat: place.geometry.location.lat, lng: place.geometry.location.lng };
                        new google.maps.Marker({
                            position: placeLatLng,
                            map: map,
                            title: place.name
                        });
                    });
                }).fail(function() {
                    alert('No places found');
                });
            }

            $('#searchPlaces').click(function() {
                // Search places using the entered type
                map.addListener('click', function(event) {
                    const lat = event.latLng.lat();
                    const lng = event.latLng.lng();
                    searchNearbyPlaces(lat, lng);
                });
            });
        </script>
    </body>
    </html>
    '''


@app.route('/weather_by_coordinates')
def weather_by_coordinates():
    lat = request.args.get('lat')
    lng = request.args.get('lng')

    params = {
        'lat': lat,
        'lon': lng,
        'appid': WEATHER_API_KEY,
        'units': 'metric'
    }
    response = requests.get(BASE_WEATHER_URL, params=params)
    data = response.json()

    if response.status_code == 200:
        temperature = data['main']['temp']
        humidity = data['main']['humidity']
        weather_description = data['weather'][0]['description']
        coordinates = data['coord']
        return jsonify({
            'temperature': temperature,
            'humidity': humidity,
            'description': weather_description,
            'coordinates': coordinates
        })
    else:
        return jsonify({'error': data.get('message')}), 404


@app.route('/nearby_cities')
def nearby_cities():
    lat = float(request.args.get('lat'))
    lng = float(request.args.get('lng'))

    nearby_cities_list = find_nearby_cities(lat, lng)

    if nearby_cities_list:
        return jsonify(nearby_cities_list)
    else:
        return jsonify({'error': 'No nearby cities found'}), 404


@app.route('/guess_city_name')
def guess_city_name():
    lat = float(request.args.get('lat'))
    lng = float(request.args.get('lng'))

    city_name = get_city_name_by_latlng(lat, lng)

    if city_name:
        return jsonify({'city': city_name})
    else:
        return jsonify({'error': 'City not found'}), 404


@app.route('/search_places')
def search_places():
    lat = float(request.args.get('lat'))
    lng = float(request.args.get('lng'))
    place_type = request.args.get('placeType')

    params = {
        'location': f'{lat},{lng}',
        'radius': 5000,  # Search within 5 km radius
        'type': place_type,
        'key': API_KEY
    }
    response = requests.get(PLACES_URL, params=params)
    data = response.json()

    if response.status_code == 200 and 'results' in data:
        return jsonify({'places': data['results']})
    else:
        return jsonify({'error': 'No places found'}), 404


if __name__ == '__main__':
    app.run(debug=True)
