"""Apply multipart request spec to aiohttp"""
from aiohttp_graphql import GraphQLView
from graphql_server import load_json_body

from ..utils import place_files_in_operations


class FileUploadGraphQLView(GraphQLView):
    """Handles multipart/form-data content type in aiohttp views"""

    async def parse_body(self, request):
        """Handle multipart request spec for multipart/form-data"""
        content_type = request.content_type
        if content_type == 'multipart/form-data':
            form = dict(await request.post())
            operations = load_json_body(form.get('operations', '{}'))
            files_map = load_json_body(form.get('map', '{}'))
            return place_files_in_operations(
                operations,
                files_map,
                request.files
            )
        return await super(FileUploadGraphQLView, self).parse_body(request)
