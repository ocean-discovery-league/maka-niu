#!/usr/bin/env python3

import logging
import sys
import tator
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    # Create a parser that includes path to media file.
    parser = tator.get_parser()
    parser.add_argument('--type_id',
                        help='Media type ID for upload.',
                        required=True, type=int)
    parser.add_argument('--media_path', help='Path to media file.', required=True)
    args = parser.parse_args()

    # Create the api using token
    tator_api = tator.get_api(args.host, '89fe3e220c88ca291e7448a143b83489e16c60d5')

    # Upload the media to new section "automatic upload test"
    for progress, response in tator.util.upload_media(tator_api, args.type_id, args.media_path, section='Automatic Upload Test'):
        logger.info(f"Upload progress: {progress}%")
        sys.stdout.flush();
    logger.info(response.message)

#commandline w arguments: python3 ./TatorUpload.py --type_id 28 --media_path /var/www/html/media/[videoNameHere].mp4
