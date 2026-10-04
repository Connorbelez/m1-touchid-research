"""Generate an unapplied error-propagation patch against the pinned snapshot."""
from pathlib import Path
import difflib

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'research/aurora-sep'
changed = {}
p = 'drivers/soc/apple/store_shim.c'
s = (BASE / p).read_text()
s = s.replace('return IS_ERR(f) ? NULL : f;', 'return f;')
s = s.replace('if (IS_ERR(f))\n\t\treturn NULL;', 'if (IS_ERR(f))\n\t\treturn f;')
s = s.replace('if (!S_ISBLK(file_inode(f)->i_mode) ||\n\t    (writable && bdev_read_only(file_bdev(f)))) {\n\t\tfilp_close(f, NULL);\n\t\treturn NULL;\n\t}', 'if (!S_ISBLK(file_inode(f)->i_mode)) {\n\t\tfilp_close(f, NULL);\n\t\treturn ERR_PTR(-ENOTBLK);\n\t}\n\tif (writable && bdev_read_only(file_bdev(f))) {\n\t\tfilp_close(f, NULL);\n\t\treturn ERR_PTR(-EROFS);\n\t}')
s = s.replace('void sep_store_close(void *handle)', '''/* Decode an open result before Rust constructs an owning StoreFile. */
int sep_store_open_error(void *handle)
{
	if (!handle)
		return -EIO;
	return IS_ERR(handle) ? PTR_ERR(handle) : 0;
}

void sep_store_close(void *handle)''')
s = s.replace('/*\n * Opens an existing file read-only, NULL if absent.', '/*\n * Opens an existing file read-only, preserving the kernel error pointer.')
changed[p] = s
p = 'drivers/soc/apple/shim.h'
s = (BASE / p).read_text().replace('void sep_store_close(void *handle);', 'int sep_store_open_error(void *handle);\nvoid sep_store_close(void *handle);')
changed[p] = s
p = 'drivers/soc/apple/shim.rs'
s = (BASE / p).read_text().replace('    fn sep_store_close(handle:', '    fn sep_store_open_error(handle: *mut c_void) -> c_int;\n    fn sep_store_close(handle:')
s = s.replace('impl StoreFile {', '''impl StoreFile {
    /// Accept only a live file; preserve every original open error.
    fn from_open_result(handle: *mut c_void) -> Result<StoreFile> {
        // SAFETY: the shim only classifies the pointer; it does not dereference it.
        let error = unsafe { sep_store_open_error(handle) };
        kernel::error::to_result(error)?;
        Ok(StoreFile { handle })
    }
''', 1)
s = s.replace('the shim returns NULL on failure.', 'the shim preserves error pointers on failure.')
for err in ['ENOENT', 'ENODEV']:
 s = s.replace(f'        if handle.is_null() {{\n            return Err({err});\n        }}\n        Ok(StoreFile {{ handle }})', '        Self::from_open_result(handle)')
changed[p] = s
patch = ''
for p,new in changed.items():
 old = (BASE/p).read_text()
 assert old != new
 patch += ''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+p,tofile='b/'+p))
(ROOT/'proposals/store-open-errors.patch').write_text(patch)
print('Generated candidate for',len(changed),'files; upstream snapshots unchanged.')
