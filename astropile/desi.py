import os
import numpy as np
import datasets
from datasets import Features, Value, Array2D, Sequence
from datasets.utils.logging import get_logger


# TODO: Add BibTeX citation
# Find for instance the citation on arxiv or on the dataset repo/website
_CITATION = """\
@InProceedings{huggingface:dataset,
title = {A great new dataset},
author={huggingface, Inc.
},
year={2020}
}
"""

# TODO: Add description of the dataset here
# You can copy an official description
_DESCRIPTION = """\
Spectra datset from DESI.
"""

# TODO: Add a link to an official homepage for the dataset here
_HOMEPAGE = ""

# TODO: Add the licence for the dataset here if you can find it
_LICENSE = ""

# Download URLs for different variants of the dataset
# TODO: these files should be versionned
_URLS = {
    "edr_sv3": {'catalog': "https://users.flatironinstitute.org/~flanusse/desi_catalog.fits",
                'data':    "https://users.flatironinstitute.org/~flanusse/desi_sv3.hdf"}
}

_VERSION = "0.0.1"

class DESIReader:
    """
    A reader for DESI data.
    """

    def __init__(self, 
                 catalog_path: str,
                    data_path: str): 
        import h5py
        from astropy.table import Table
        
        self._catalog = Table.read(catalog_path)
        self._data_path = data_path
        # self._data = h5py.File(data_path, 'r')

    @classmethod
    @property
    def urls(cls):
        return _URLS

    @classmethod
    @property
    def features(cls):
        return Features({
            'spectrum': Array2D(shape=(None, 2), dtype='float32'), # Stores flux and ivar
            'lambda_min': Value('float32'), # Min and max wavelength
            'lambda_max': Value('float32'),
            'resolution': Value('float32'), # Resolution of the spectrum
            'z': Value('float32'),
            'ebv': Value('float32'),
            # And so on...
        })

    @property
    def catalog(self):
        return self._catalog

    def get_examples(self, keys = None):
        import h5py

        # If no keys are provided, return all the examples
        if keys is None:
            keys = self._catalog['TARGETID']

        # Preparing an index for fast searching through the catalog
        sort_index = np.argsort(self._catalog['TARGETID'])
        sorted_ids = self._catalog['TARGETID'][sort_index]

        with h5py.File(self._data_path, 'r') as data:
            # Loop over the indices and yield the requested data
            for i, id in enumerate(keys):
                # Extract the indices of requested ids in the catalog 
                idx = sort_index[np.searchsorted(sorted_ids, id)]
                row = self._catalog[idx]
                key = row['TARGETID']

                example = {
                    'spectrum':  np.stack([data['flux'][idx],
                                                    data['ivar'][idx]], axis=1).astype('float32'),# TODO: add correct values
                    'lambda_min': np.array([0.]).astype('float32'),  # TODO: add correct values
                    'lambda_max': np.array([1.]).astype('float32'),  # TODO: add correct values
                    'resolution': np.array([0.1]).astype('float32'),
                    'z': np.array([row['Z']]).squeeze().astype('float32'),
                    'ebv':np.array([ row['EBV']]).squeeze().astype('float32'),
                }

                # Checking that we are retriving the correct data
                assert (key == keys[i]) & (data['target_ids'][idx] == keys[i]) , ("There was an indexing error when reading desi spectra", (key, keys[i]))

                yield str(key), example


class DESI(datasets.GeneratorBasedBuilder):
    """TODO: Short description of my dataset."""

    VERSION = _VERSION

    BUILDER_CONFIGS = [
        datasets.BuilderConfig(name="edr_sv3", version=VERSION, 
                               description="One percent survey from the DESI Early Data Release."),
    ]

    DEFAULT_CONFIG_NAME = "edr_sv3"

    def _info(self):
        """ Defines the features available in this dataset.
        """
        return datasets.DatasetInfo(
            # This is the description that will appear on the datasets page.
            description=_DESCRIPTION,
            # This defines the different columns of the dataset and their types
            features=DESIReader.features,
            # Homepage of the dataset for documentation
            homepage=_HOMEPAGE,
            # License for the dataset if available
            license=_LICENSE,
            # Citation for the dataset
            citation=_CITATION,
        )

    def _split_generators(self, dl_manager):
        # First, attempt to access the files locally, if unsuccessful, emit a warning and attempt to download them
        if dl_manager.manual_dir is not None:
            data_dir = dl_manager.manual_dir
            data_dir = {k: os.path.join(data_dir, _URLS[self.config.name][k].split('/')[-1]) 
                        for k in _URLS[self.config.name]}
        else:
            logger.warning("We recommend downloading data manually through GLOBUS" 
                           "and specifying the manual_dir argument to pass to the dataset builder."
                           "Downloading data automatically through the dataset builder will proceed but is not recommended.")
            data_dir = dl_manager.download_and_extract(_URLS[self.config.name])

        return [
            datasets.SplitGenerator(
                name=datasets.Split.TRAIN,
                gen_kwargs={**data_dir}
            )
        ]

    def _generate_examples(self, catalog, data):
        """ Yields examples as (key, example) tuples.
        """
        reader = DESIReader(catalog, data)
        for key, example in reader.get_examples():
            yield key, example