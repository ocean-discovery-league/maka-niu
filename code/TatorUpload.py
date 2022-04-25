#!/usr/bin/env python3

import os
import sys
import tator
import socket
import logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)  # logging.DEBUG is an option
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    # Create a parser that includes path to media file.
    parser = tator.get_parser()
    parser.add_argument('--type_id',
                        help='Media type ID for upload.',
                        required=True, type=int)
    parser.add_argument('--media_path', help='Path to media file.', required=True)
    parser.add_argument('--media_id', help='Attach to existing media id.', required=False)
    args = parser.parse_args()

    # Create the api using token
    #tator_api = tator.get_api(args.host, '89fe3e220c88ca291e7448a143b83489e16c60d5')  #pbell's token
    tator_api = tator.get_api(args.host, 'e805c7191bf325527e289a315b03b8fb45310ce5')  #makaniu upload's token

    # we use hostname to as the project section name
    hostname = socket.gethostname()

    # lookup our project id
    #media_types = tator_api.get_media_type(args.type_id)
    #project_id = media_types.project
    project_id = 18

    # lookup our section id
    section_id = False
    sections = tator_api.get_section_list(project_id)
    for section in sections:
        if section.name == hostname:
            section_id = section.id
            break

    logger.info(f"section_id: {section_id}")

    # check if is this is a duplicate upload
    fname = os.path.basename(args.media_path)
    duplicate = False
    if fname == 'tatorfile.jpg':
        pass
    elif section_id != False:
        medias = tator_api.get_media_list(project_id, section=section_id)
        for media in medias:
            if media.name == fname:
                duplicate = True
                break
            if media.media_files != None and media.media_files.attachment != None:
                for attachment in media.media_files.attachment:
                    if attachment.name == fname:
                        duplicate = True
                        break
            if duplicate:
                break
                    
    if duplicate:
        print('skipping upload of duplicate file', fname)
        sys.stdout.flush()
        sys.exit()

    if not args.media_id:
        for progress, response in tator.util.upload_media(tator_api, args.type_id, args.media_path, section=hostname):
            logger.info(f"Upload progress: {progress}%")
            sys.stdout.flush()
        logger.info(response.message)
    else:
        # see https://www.tator.io/tutorials/2021-05-19-attach-files-to-media/
        media_id = int(args.media_id)
        for progress, response in tator.util.upload_attachment(tator_api, media_id, args.media_path):
            logger.info(f"Upload progress: {progress}%")
            sys.stdout.flush()
        logger.info(response.message)

# commandline w arguments:
# $ python3 ./TatorUpload.py --type_id 28 --media_path /var/www/html/media/[videoNameHere].mp4
# or, for attachments
# $ python3 ./TatorUpload.py --type_id 28 --media_id 1695015 --media_path /var/www/html/media/[sensordatafile].txt
# in the second one type_id is ignored and can be anything (but is still required)
