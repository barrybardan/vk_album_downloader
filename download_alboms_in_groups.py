import vk_api
import requests
import os
import re
import datetime
import sys
import pprint

def handler_captcha(captcha):
    key = input(f'Enter captcha code {captcha.get_url()}: ').strip()
    return captcha.try_again(key)

path_to_downloaded_albums = 'vk_downloaded_albums'
path_to_user_data = 'data.txt'
path_to_albums_list = 'groups_list.txt'


def print_progress(value, end_value, bar_length=20):
    percent = float(value) / end_value
    arrow = '-' * int(round(percent * bar_length) - 1) + '>'
    spaces = ' ' * (bar_length - len(arrow))

    sys.stdout.write("\rProgress: [{0}] {1}% ({2} / {3})".format(
        arrow + spaces, int(round(percent * 100)),
        value, end_value))
    sys.stdout.flush()


def process_url_old(url):
    verification = re.compile(r'^https://vk.com/album(-?[\d]+)_([\d]+)$')
    o = verification.match(url)
    if not o:
        raise ValueError('invalid album link: {}'.format(url))
    owner_id = o.group(1)
    album_id = o.group(2)
    return {'owner_id': owner_id, 'album_id': album_id}




def read_login_information():
    lines = []
    try:
        with open(path_to_user_data, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError as e:
        print(e)
        print('please, fix the file name either in the folder or in the script')
        sys.exit(e.errno)

    if (lines.__len__() < 2):
        print('unable to read login / phone number and password')
        print('please, check your user data in the file')
        sys.exit(1)
    l = lines[0]
    p = lines[1]
    return l, p

def read_data(api):


    queries = []
    try:
        with open(path_to_albums_list, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError as e:
        print(e)
        print('please, fix the file name either in the folder or in the script')
        sys.exit(e.errno)

    queries = []
    for url in lines:
        try:
            queries.extend(process_url(clear_url_after_question(url),api))
        except ValueError as e:
            print(e)
    return queries

def process_url(url, api):
    verification = re.compile(r'^https://vk.com/public(-?[\d]+)$')
    o = verification.match(url)
    if not o:
        raise ValueError('invalid public link: {}'.format(url))
    owner_id = -int(o.group(1))
    print(owner_id)
    album_id = 0
    # albums = api.photos.getAlbums(owner_id)
    album_info = api.photos.getAlbums(owner_id=owner_id)
    print('got alboms')
    pprint.pprint(album_info)
    queries = []
    for album in album_info['items']:
        queries.append({'owner_id': owner_id,  'album_id': album['id']})

    return queries


def download_image(url, local_file_name):
    response = requests.get(url, stream=True)
    if not response.ok:
        print('bad response:', response)
        return
    # print(local_file_name)   
    local_file_name = clear_url_after_question(local_file_name) 
    # print(local_file_name)
    try:     
        with open(local_file_name, 'wb') as file:
            for chunk in response.iter_content(1024):
                # if not chunk:
                #     break
                file.write(chunk)
    except:            
        print(local_file_name)
    return

def clear_url_after_question(url):
    parts = url.split('?')
    return parts[0] 



def fix_illegal_album_title(title):
    illegal_character = '\/|:?<>*"'
    for c in illegal_character:
        title = title.replace(c, '_')
    return title


def main():

    l, p  = read_login_information()

    vk_session = vk_api.VkApi(l, p, captcha_handler=handler_captcha)
    api = vk_session.get_api()
    try:
        vk_session.auth()
    except Exception as e:
        print('could not authenticate to vk.com')
        print(e)
        print('please, check your user data in the file')
        sys.exit(1)



    queries = read_data(api)
 

    print('number of albums to download: {}'.format(queries.__len__()))
    for q in queries:
        o = q['owner_id']
        a = q['album_id']

        try:
            album = api.photos.getAlbums(owner_id=o, album_ids=a)['items'][0]
            title = album['title'].strip()
            title = fix_illegal_album_title(title)

            photos = []

            total_images = album['size']
            current_offset = 0
            number_to_fetch = 1000
            while current_offset < total_images:
                print(current_offset)
                photos = photos + api.photos.get(owner_id=o, album_id=a, photo_sizes=1, count=number_to_fetch, offset=current_offset)['items']
                current_offset = current_offset + number_to_fetch
               
#           if images_num > 1000:
#                images_num = 1000
#            photos = api.photos.get(owner_id=o, album_id=a, photo_sizes=1, count=images_num, offset=999)['items']
        except vk_api.exceptions.ApiError as e:
            print('while getting albom:' + a)
            print('exception:')
            print(e)
            continue

        album_path = path_to_downloaded_albums + '/' + title
        if not os.path.exists(album_path):
            os.makedirs(album_path)
        else:
            album_path += '.copy_{:%Y-%m-%d_%H-%M-%S}'.format(
                datetime.datetime.now())
            os.makedirs(album_path)

        print('downloading album: ' + title)
        cnt = 0
        for p in photos:
            largest_image_width = p['sizes'][0]['width']
            largest_image_src = p['sizes'][0]['url']

            if largest_image_width == 0:
                largest_image_src = p['sizes'][p['sizes'].__len__() - 1]['url']
            else:
                for size in p['sizes']:
                    if size['width'] > largest_image_width:
                        largest_image_width = size['width']
                        largest_image_src = size['url']

            extension = os.path.splitext(largest_image_src)[-1]
            # print(album_path)
            download_image(largest_image_src, album_path + '/' +
                           str(p['id']) + extension)
            cnt += 1
            print_progress(cnt, total_images)
        print()


if __name__ == "__main__":
    main()
