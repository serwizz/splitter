#!/usr/bin/env python

import glob
import os
import pathlib
import shutil
from subprocess import call


class AlbumSplitter:
    def __init__(self, album) -> None:
        self.album = album
        self._cue_file = None
        self._flac_file = None
        self._get_cue_file()
        self._get_flac_file()

    def split(self):
        if not self._get_cue_file():
            return

        self._prepare_cue()
        self._convert_to_flac()
        self._split_flac()
        self._remove_flac()
        self._set_tags()
        self._sanitize_filenames()
        self._remove_trash()

    def _prepare_cue(self):
        """
        sed -i '1s/^\xEF\xBB\xBF//' *.cue
        """
        cue_file = self._get_cue_file()

        path = pathlib.Path(cue_file)
        text = path.read_text()
        text = text.replace('\xEF\xBB\xBF', '')
        path.write_text(text)

        return cue_file

    def _convert_to_flac(self):
        """
        sox *.wav file.flac
        sox *.wv file.flac
        shntool conv -o flac *.ape
        """
        wav = self._first('*.wav') or self._first('*.wv')
        if wav:
            self._run_cmd(['sox', '-S', wav, 'file.flac'])
        ape = self._first('*.ape')
        if ape:
            self._run_cmd(['shntool', 'conv', '-o', 'flac', ape])

    def _split_flac(self):
        """shnsplit -f *.cue -t '%n - %t' -o flac *flac"""
        self._run_cmd(['shnsplit', '-f', self._get_cue_file(), '-t', '%n - %t', '-o', 'flac', self._get_flac_file()])

    def _remove_flac(self):
        """
        find *.flac -not -regex '[0-9].*flac' -delete
        rm 00\ -\ pregap.flac
        """
        os.remove(self._flac_file)
        pregap_file = pathlib.Path(self.album, '00 - pregap.flac')
        if pregap_file.exists():
            os.remove(pregap_file)

    def _set_tags(self):
        """
        cuetag.sh *.cue *.flac
        """
        self._run_cmd(['cuetag.sh', self._get_cue_file()] + self._all('*.flac'))

    def _sanitize_filenames(self):
        """
        rename -v ':' '' *.flac
        rename -v '?' '' *.flac
        """
        for flac in self._all('*.flac'):
            newname = flac.replace(':', '')
            newname = newname.replace('?', '')
            if newname != flac:
                os.rename(flac, newname)

    def _remove_trash(self):
        """
        rm *.log
        rm -r Scans
        rm -r Covers
        rm *.ape
        rm *.cue
        rm *.wv
        rm *.wav
        """

        files_to_remove = ('*.log', '*.ape', '*.cue', '*.wv', '*.wav')
        for wildcard in files_to_remove:
            for file in self._all(wildcard=wildcard):
                os.remove(file)

        folders_to_remove = ('Scans', 'Covers', 'scans', 'covers', 'Artwork', 'artwork')
        for folder in folders_to_remove:
            shutil.rmtree(pathlib.Path(self.album, folder), ignore_errors=True)

    def _get_cue_file(self):
        if not self._cue_file:
            self._cue_file = self._first('*.cue')
        return self._cue_file

    def _get_flac_file(self):
        if not self._flac_file:
            self._flac_file = self._first('*.flac')
        return self._flac_file

    def _first(self, wildcard):
        files = self._all(wildcard=wildcard)
        return files[0] if files else None

    def _all(self, wildcard):
        items = glob.glob(f'{self.album}/{wildcard}')
        items.sort()
        return items

    def _run_cmd(self, cmd):
        cmd = list(map(str, cmd))
        call(cmd, cwd=self.album)


class Split:
    def cur_dir(self):
        return pathlib.Path().resolve()

    def run(self):
        current_dir = self.cur_dir()
        self._process_folder(current_dir)

    def _process_folder(self, folder):
        subfolders = [f.path for f in os.scandir(folder) if f.is_dir()]
        subfolders.sort()
        for subfolder in subfolders:
            album_splitter = AlbumSplitter(album=pathlib.Path(folder, subfolder))
            album_splitter.split()
            self._process_folder(folder=subfolder)


Split().run()
