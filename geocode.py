import httplib2
import json, requests
import sys
import codecs
sys.stdout = codecs.getwriter('utf8')(sys.stdout)
sys.stderr = codecs.getwriter('utf8')(sys.stderr)

def getGeocodeLocation(inputString):
    google_api_key = "AIzaSyDhbfNoX5i7euOcHdpjZ9EMJYdbR1GWlxo"
    locationString = inputString.replace(" ", "+")
    url = ('https://maps.googleapis.com/maps/api/geocode/json?address={0}&key={1}'.format(locationString, google_api_key))
    h = httplib2.Http()
    response, content = h.request(url, 'GET')
    result = json.loads(content)
    latitude = result['results'][0]['geometry']['location']['lat']
    longitude = result['results'][0]['geometry']['location']['lng']
    return(latitude, longitude)

def findARestaurant(mealType, locationString):
    location = getGeocodeLocation(locationString)
    url = 'https://api.foursquare.com/v2/venues/explore'
    params = dict(
        client_id='GZO5GCT3V1PK0WMYN35JMQXTL4Q0BPVGPJWERUN50MF5IS0K',
        client_secret='I23U3EVRZIBSPD0KS2LAAENVVPVXLZZQ1I4OSL5CZEE04W1A',
        v='20180323',
        ll='{0},{1}'.format(location[0], location[1]),
        query=mealType,
        limit=1
    )
    resp = requests.get(url=url, params=params)
    data = json.loads(resp.text)

    venue = data['response']['groups'][0]['items'][0]['venue']
    venueAddress = venue['location']['formattedAddress']

    if venue:
        photoParams = dict(
            client_id='GZO5GCT3V1PK0WMYN35JMQXTL4Q0BPVGPJWERUN50MF5IS0K',
            client_secret='I23U3EVRZIBSPD0KS2LAAENVVPVXLZZQ1I4OSL5CZEE04W1A',
            v='20180323'
        )
        photosUrl = 'https://api.foursquare.com/v2/venues/{0}/photos'.format(venue['id'])
        photoResp = requests.get(photosUrl, params=photoParams)
        photoData = json.loads(photoResp.text)
        if photoData['response']['photos']['count'] != 0:
            photo = photoData['response']['photos']['items'][0]
            photoUrl = '{0}300x300{1}'.format(photo['prefix'], photo['suffix'])
        else:
            photoUrl = 'https://igx.4sqi.net/img/general/300x300/default.jpg'

        sys.stdout.write(venue['name'] + '\n')
        for line in venueAddress:
            sys.stdout.write(line + '\n')

        results = dict(
            name=venue['name'],
            address=venueAddress,
            image=photoUrl
        )

        return results

    else:
        print("No results found")
        return None