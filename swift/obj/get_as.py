# Copyright (c) 2014 Vyacheslav Rafalskiy
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

""" get_as Extension to Object Server for Swift """

import io
import zipfile
import uuid

from swift.common.swob import Response, \
    HTTPBadRequest, HTTPNotFound, HTTPUnprocessableEntity, \
    HTTPMethodNotAllowed, HTTPRequestEntityTooLarge

MAX_CONTENT_SIZE = 100000000  # Cap at 100M
_boundary = str(uuid.uuid4())


def dump_response(resp):
    parts = ['{}: {}'.format(h, v)
             for h, v in resp.headers.items()] + ['', resp.body]
    return '\r\n'.join(parts)


def zip_list_content_response(fp):
    with zipfile.ZipFile(fp) as zip_file:
        body = ('\r\n'.join(zip_file.namelist()) + '\r\n').encode('utf-8')
        return Response(status=200, content_type='text/plain', body=body)


def zip_get_content_response(fp, files, boundary=_boundary):
    def part_with_attachment(fn):
        part = Response(headers={
            'Content-Type': 'application/octet-stream',
            'Content-Disposition': 'attachment; filename=%s' %
            fn.encode('utf-8'),
            })
        part.body = zip_file.read(fn)
        return part

    with zipfile.ZipFile(fp) as zip_file:
        try:
            total_size = sum(zip_file.getinfo(fn).file_size for fn in files)
        except KeyError:
            raise HTTPNotFound(body='File not found in the zip\r\n')

        if total_size > MAX_CONTENT_SIZE:
            raise HTTPRequestEntityTooLarge()

        if len(files) == 1:
            resp = part_with_attachment(files[0])
        else:
            resp = Response(
                content_type='multipart/mixed; boundary=%s' % boundary)
            body = io.BytesIO()
            for fn in files:
                part_resp = part_with_attachment(fn)
                body.write('\r\n--%s\r\n' % boundary)
                body.write(dump_response(part_resp))

            body.write('\r\n--%s--\r\n' % boundary)
            resp.body = body.getvalue()

    return resp


def get_as(query, fp):
    if query.get('as') == 'zip':
        try:
            if 'list_content' in query:
                return zip_list_content_response(fp)
            elif 'get_content' in query:
                return zip_get_content_response(
                    fp, query['get_content'].split(','))
            else:
                raise HTTPMethodNotAllowed(
                    body='No such operation is defined on zip file\r\n')
        except zipfile.BadZipfile:
            raise HTTPUnprocessableEntity(body='Bad zip file\r\n')
    else:
        raise HTTPBadRequest(body='Unknown "as" type\r\n')
