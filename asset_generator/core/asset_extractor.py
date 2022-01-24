# encoding: utf-8
"""

"""
__author__ = 'Richard Smith'
__date__ = '01 Jun 2021'
__copyright__ = 'Copyright 2018 United Kingdom Research and Innovation'
__license__ = 'BSD - see LICENSE file in top-level package directory'
__contact__ = 'richard.d.smith@stfc.ac.uk'


# Framework imports
from asset_scanner.core import BaseExtractor
from asset_scanner.core.item_describer import ItemDescription
from asset_scanner.core.utils import dict_merge, generate_id
from asset_scanner.types.source_media import StorageType
from asset_scanner.plugins.extraction_methods import utils as item_utils

# Python imports
from functools import lru_cache
import re
from typing import Optional
import logging



LOGGER = logging.getLogger(__name__)


class AssetExtractor(BaseExtractor):
    """
    The central class for the asset extraction process.

    An instance of the class can be used to atomically process files
    passed to its ``process_file`` method.
    """

    PROCESSOR_ENTRY_POINT = 'asset_generator.media_handlers'

    @lru_cache(maxsize=3)
    def _load_processor(self, name: StorageType):
        
        name = name.value
        processor_kwargs = self.conf.get(
            'media_handlers', {}
        ).get(
           name, {} 
        )
        
        return self.processors.get_processor(name, **processor_kwargs)
    
    def get_collection_id(self, description: ItemDescription, filepath: str, storage_media: StorageType) -> str:
        """Return the collection ID for the file."""
        collection_id = getattr(description.collections, 'id', 'undefined')
        return generate_id(collection_id)

    def run_processors(self,
                       filepath: str,
                       description: ItemDescription,
                       source_media: StorageType = StorageType.POSIX,
                       **kwargs: dict) -> dict:
        """
        Extract the raw facets from the file based on the listed processors

        :param filepath: Path to the file
        :param description: ItemDescription
        :param source_media: The source media type (POSIX, Object, Tape)

        :return: result from the processing
        """
        # Get default tags
        tags = description.facets.defaults

        # Execute facet extraction functions
        processors = description.facets.extraction_methods

        for processor in processors:

            metadata = self._run_facet_processor(processor, filepath, source_media)

            # Merge the extracted metadata with the metadata already retrieved
            if metadata:
                tags = dict_merge(tags, metadata)

        # Process multi-values

        # Apply mappings

        # Apply overrides

        # Convert to URIs

        # Process URIs to human terms

        return tags

    def process_file(self, filepath: str, source_media: StorageType, checksum: Optional[str] = None, **kwargs) -> None:
        """

        :param filepath:
        :param source_media:
        :param checksum:
        :return:

        """
        processor = self._load_processor(source_media)

        data = processor.run(filepath, source_media, checksum, **kwargs)

        # Get dataset description file
        if self.item_descriptions:

            description = self.item_descriptions.get_description(filepath)
            categories = self.get_categories(filepath, source_media, description)
            data['body']['categories'] = categories

            # Get facet values
            processor_output = self.run_processors(filepath, description, source_media, **kwargs)
            properties = processor_output.get('properties', {})

            # Get collection id
            coll_id = self.get_collection_id(description, filepath, source_media)

            # Generate item id
            item_id = item_utils.generate_item_id_from_properties(
            filepath,
            coll_id,
            properties,
            description
            )

            data['body']['properties'] = properties
            data['body']['item_id'] = item_id

        self.output(filepath, source_media, data, namespace="asset")

        message_body = {
            "item_id": item_id,
            "filepath": filepath
        }

        self.output(filepath, source_media, message_body, namespace="header")
