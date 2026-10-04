"""Compile actual C open helpers with injected failures, never opening a device.

This covers C error preservation and the old Rust mapping's consequence.
It is not a full kernel or Rust integration build.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'research/aurora-sep'


def function(source, signature):
    start = source.index(signature)
    body = source.index('{', start)
    depth = 1
    end = body + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


@unittest.skipUnless(shutil.which('cc'), 'C compiler required')
class StorageOpenErrors(unittest.TestCase):
    def test_injected_open_errors_are_preserved(self):
        with tempfile.TemporaryDirectory(prefix='sep-storage-research-') as temp:
            tmp = Path(temp)
            for name in ['store_shim.c', 'shim.h', 'shim.rs']:
                rel = Path('drivers/soc/apple') / name
                (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(BASE / rel, tmp / rel)
            subprocess.run(['git', 'apply', str(ROOT / 'proposals/store-open-errors.patch')],
                           cwd=tmp, check=True)
            old = (BASE / 'drivers/soc/apple/store_shim.c').read_text()
            new = (tmp / 'drivers/soc/apple/store_shim.c').read_text()
            definitions = []
            for name in ['sep_store_open', 'sep_store_open_trunc', 'sep_store_open_ro']:
                signature = f'void *{name}(const char *path)'
                definitions.append(function(old, signature).replace(name+'(', 'old_'+name+'(', 1))
                definitions.append(function(new, signature))
            definitions.append(function(new, 'int sep_store_open_error(void *handle)'))
            harness = r'''
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#ifndef O_LARGEFILE
#define O_LARGEFILE 0
#endif
#define ERR_PTR(e) ((void *)(intptr_t)(e))
#define PTR_ERR(p) ((intptr_t)(p))
#define IS_ERR(p) ((uintptr_t)(p) >= (uintptr_t)-4095)
struct file { int marker; };
static int injected;
static struct file valid;
static struct file *open_as_kernel(const char *path, int flags, unsigned mode)
{
    (void)path; (void)flags; (void)mode;
    return injected ? ERR_PTR(-injected) : &valid;
}
DEFINITIONS
int main(void)
{
    void *(*before[])(const char *) = {
        old_sep_store_open, old_sep_store_open_trunc, old_sep_store_open_ro};
    void *(*after[])(const char *) = {
        sep_store_open, sep_store_open_trunc, sep_store_open_ro};
    int errors[] = {ENOENT, EIO, EACCES, ENOMEM, ELOOP, ENOTDIR, EROFS, ENOSPC};
    unsigned checks = 0;
    for (unsigned op = 0; op < 3; op++) {
        for (unsigned i = 0; i < sizeof(errors)/sizeof(errors[0]); i++) {
            injected = errors[i];
            void *old = before[op]("synthetic");
            /* Existing shim.rs maps this NULL to ENOENT for all file opens. */
            assert(old == NULL);
            assert(sep_store_open_error(after[op]("synthetic")) == -errors[i]);
            checks++;
        }
        injected = 0;
        assert(before[op]("synthetic") == &valid);
        assert(after[op]("synthetic") == &valid);
        assert(sep_store_open_error(&valid) == 0);
        checks++;
    }
    assert(sep_store_open_error(NULL) == -EIO);
    printf("%u open cases passed; unexpected NULL rejects with EIO\n", checks);
    return 0;
}
'''.replace('DEFINITIONS', '\n'.join(definitions))
            src, exe = tmp/'harness.c', tmp/'harness'
            src.write_text(harness)
            subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(src),'-o',str(exe)],check=True)
            result = subprocess.run([str(exe)],check=True,capture_output=True,text=True)
            self.assertIn('27 open cases passed', result.stdout)
            print(result.stdout.strip())


if __name__ == '__main__':
    unittest.main()
