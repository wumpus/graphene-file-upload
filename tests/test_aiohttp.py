import json
from tempfile import NamedTemporaryFile
import pytest
import io

import graphene
from graphene_file_upload.scalars import Upload
from aiohttp.test_utils import TestClient, TestServer, loop_context

from .aiohttp_app import create_app


class Query(graphene.ObjectType):
    ok = graphene.Boolean(default_value=True)


class MyUpload(graphene.Mutation):
    class Arguments:
        file_in = Upload()

    ok = graphene.Boolean()
    first_line = graphene.String()

    def mutate(self, info, file_in):
        #print('GREG server file_in', file_in)
        #print('GREG server type file_in', type(file_in))
        #print('GREG server isinstance IOBase', isinstance(file_in, io.IOBase))
        #print('GREG server file_in file', file_in.file)
        #print('GREG server type file_in file', type(file_in.file))
        #print('GREG server isinstance IOBase file', isinstance(file_in.file, io.IOBase))

        first_line = file_in.readline().strip().decode('utf-8')
        file_in.seek(0)
        return MyUpload(ok=True, first_line=first_line)


class Mutation(graphene.ObjectType):
    my_upload = MyUpload.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)


async def response_utf8_json(resp):
    body = await resp.read()
    return json.loads(body.decode())


async def single_file_helper(client, t_file, expected_first_line):
    query = '''
        mutation testMutation($file: Upload!) {
            myUpload(fileIn: $file) {
                ok
                firstLine
            }
        }
    '''
    response = await client.post(
        '/graphql',
        data={
            'operations': json.dumps({
                'query': query,
                'variables': {
                    'file': None,
                },
            }),
            't_file': t_file,
            'map': json.dumps({
                't_file': ['variables.file'],
            }),
        }
    )

    if response.status != 200:
        print('about to crash, response body is:')
        print(await response_utf8_json(response))

    assert response.status == 200
    assert await response_utf8_json(response) == {
        'data': {
            'myUpload': {
                'ok': True,
                'firstLine': expected_first_line,
            },
        }
    }


@pytest.fixture
def loop():
    with loop_context() as loop:
        yield loop


@pytest.fixture
def app():
    return create_app(schema=schema)


@pytest.fixture
def test_client(loop, app):
    async def make_client():
        return TestClient(TestServer(app, loop=loop), loop=loop)

    client = loop.run_until_complete(make_client())

    loop.run_until_complete(client.start_server())
    yield client
    loop.run_until_complete(client.close())


async def test_single_file(loop, test_client):
    tests = (
        (u'Fake Data\nLine2\n', u'Fake Data'),
        # Try the fire emoji
        (u'\U0001F525\nLine2\nLine3\n', u'\U0001F525'),
    )
    for file_text, expected_first_line in tests:
        # don't use NamedTemporaryFile here because of https://bugs.python.org/issue33762
        # (t_file.file was OK for NamedTemporaryFile())
        #with NamedTemporaryFile() as t_file:

        with io.BytesIO(file_text.encode('utf-8')) as t_file:
            #t_file.write(file_text.encode('utf-8'))
            t_file.seek(0)
            await single_file_helper(test_client, t_file, expected_first_line)
