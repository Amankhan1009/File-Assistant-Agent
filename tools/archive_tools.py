# =============================================================================
# Standard Library Imports
# =============================================================================


import shutil

from pathlib import Path
from typing import Any
from zipfile import (
    BadZipFile,
    ZIP_DEFLATED,
    ZipFile,
)


# =============================================================================
# Third-Party Imports
# =============================================================================


from langchain_core.tools import tool


# =============================================================================
# Project Imports
# =============================================================================


from core.paths import (
    PathSecurityError,
    resolve_workspace_path,
)

from tools.common import (
    MAX_ARCHIVE_ENTRIES,
    MAX_EXTRACTED_BYTES,
    error_result,
)

from tools.schemas import (
    CompressPathsInput,
    ExtractArchiveInput,
)


# =============================================================================
# Compress Paths Tool
# =============================================================================


@tool(args_schema=CompressPathsInput)
def compress_paths(
    paths: list[str],
    destination: str,
) -> dict[str, Any]:
    """
    Create a ZIP archive from one or more files or directories
    inside the allowed workspace.

    Empty directories are preserved. Overlapping sources are
    deduplicated. Existing destinations are never overwritten.
    Partial archives are removed if archive creation fails.
    """
    destination_path: Path | None = None

    try:

        # =====================================================================
        # Resolve Workspace Root
        # =====================================================================


        workspace_root = resolve_workspace_path(".")


        # =====================================================================
        # Resolve and Validate Destination
        # =====================================================================


        destination_path = resolve_workspace_path(destination)


        if destination_path.suffix.casefold() != ".zip":
            return error_result(
                "invalid_archive_extension",
                "Destination archive must use the .zip extension.",
            )


        if destination_path.exists():
            return error_result(
                "already_exists",
                f"Destination path already exists: {destination}",
            )


        destination_parent = destination_path.parent


        if not destination_parent.exists():
            return error_result(
                "parent_not_found",
                (
                    "Destination parent directory does not exist: "
                    f"{destination}"
                ),
            )


        if not destination_parent.is_dir():
            return error_result(
                "parent_not_directory",
                (
                    "Destination parent path is not a directory: "
                    f"{destination}"
                ),
            )


        # =====================================================================
        # Resolve and Validate Source Paths
        # =====================================================================


        resolved_sources: list[tuple[str, Path]] = []


        for source in paths:

            source_path = resolve_workspace_path(source)


            if not source_path.exists():
                return error_result(
                    "not_found",
                    f"Source path does not exist: {source}",
                )


            if source_path == workspace_root:
                return error_result(
                    "protected_path",
                    "The workspace root cannot be compressed directly.",
                )


            if source_path.is_dir():

                try:
                    destination_path.relative_to(source_path)

                except ValueError:
                    pass

                else:
                    return error_result(
                        "invalid_destination",
                        (
                            "The destination archive cannot be created "
                            "inside a source directory."
                        ),
                    )


            resolved_sources.append(
                (
                    source,
                    source_path,
                )
            )


        # =====================================================================
        # Collect Unique Archive Entries
        # =====================================================================


        file_entries: dict[str, Path] = {}

        empty_directory_entries: set[str] = set()


        for _, source_path in resolved_sources:

            # -----------------------------------------------------------------
            # Regular File Source
            # -----------------------------------------------------------------


            if source_path.is_file():

                archive_name = source_path.relative_to(
                    workspace_root
                ).as_posix()


                file_entries.setdefault(
                    archive_name,
                    source_path,
                )

                continue


            # -----------------------------------------------------------------
            # Directory Source
            # -----------------------------------------------------------------


            for candidate in source_path.rglob("*"):

                archive_name = candidate.relative_to(
                    workspace_root
                ).as_posix()


                if candidate.is_file():

                    file_entries.setdefault(
                        archive_name,
                        candidate,
                    )

                    continue


                if not candidate.is_dir():
                    continue


                try:
                    next(candidate.iterdir())

                except StopIteration:

                    empty_directory_entries.add(
                        archive_name.rstrip("/") + "/"
                    )


        # =====================================================================
        # Preserve Empty Source Directory
        # =====================================================================


        for _, source_path in resolved_sources:

            if not source_path.is_dir():
                continue


            try:
                next(source_path.iterdir())

            except StopIteration:

                archive_name = source_path.relative_to(
                    workspace_root
                ).as_posix()


                empty_directory_entries.add(
                    archive_name.rstrip("/") + "/"
                )


        # =====================================================================
        # Remove Redundant Empty Directory Entries
        # =====================================================================


        empty_directory_entries = {
            directory_name
            for directory_name in empty_directory_entries
            if directory_name.rstrip("/")
            not in file_entries
        }


        # =====================================================================
        # Create ZIP Archive
        # =====================================================================


        with ZipFile(
            destination_path,
            mode="x",
            compression=ZIP_DEFLATED,
        ) as archive:

            # -----------------------------------------------------------------
            # Write Regular Files
            # -----------------------------------------------------------------


            for archive_name in sorted(file_entries):

                archive.write(
                    file_entries[archive_name],
                    arcname=archive_name,
                )


            # -----------------------------------------------------------------
            # Write Empty Directories
            # -----------------------------------------------------------------


            for directory_name in sorted(
                empty_directory_entries
            ):

                archive.writestr(
                    directory_name,
                    "",
                )


        # =====================================================================
        # Return Successful Result
        # =====================================================================


        return {
            "ok": True,
            "paths": paths,
            "destination": destination,
            "archived_files": len(file_entries),
            "archived_empty_directories": len(
                empty_directory_entries
            ),
            "created": True,
        }


    # =========================================================================
    # Workspace Security Error
    # =========================================================================


    except PathSecurityError as exc:

        return error_result(
            "path_security_error",
            str(exc),
        )


    # =========================================================================
    # Filesystem or Archive Error
    # =========================================================================


    except OSError:

        # ---------------------------------------------------------------------
        # Remove Partial Archive
        # ---------------------------------------------------------------------


        if (
            destination_path is not None
            and destination_path.exists()
            and destination_path.is_file()
        ):

            try:
                destination_path.unlink()

            except OSError:
                pass


        return error_result(
            "filesystem_error",
            "Unable to create ZIP archive.",
        )


# =============================================================================
# Extract Archive Tool
# =============================================================================


@tool(args_schema=ExtractArchiveInput)
def extract_archive(
    archive: str,
    destination: str,
) -> dict[str, Any]:
    """
    Extract a ZIP archive into an existing empty directory
    inside the allowed workspace.

    Archive entries are validated before extraction. Path traversal,
    symbolic links, excessive entry counts, and excessive extracted
    sizes are rejected.

    Existing destination contents are never overwritten.
    Partial extracted contents are removed if extraction fails.
    """
    destination_path: Path | None = None

    try:

        # =====================================================================
        # Resolve Workspace Root
        # =====================================================================


        workspace_root = resolve_workspace_path(".")


        # =====================================================================
        # Resolve and Validate Archive
        # =====================================================================


        archive_path = resolve_workspace_path(archive)


        if not archive_path.exists():
            return error_result(
                "not_found",
                f"Archive does not exist: {archive}",
            )


        if not archive_path.is_file():
            return error_result(
                "not_a_file",
                f"Archive path is not a file: {archive}",
            )


        if archive_path.suffix.casefold() != ".zip":
            return error_result(
                "invalid_archive_extension",
                "Archive must use the .zip extension.",
            )


        # =====================================================================
        # Resolve and Validate Destination
        # =====================================================================


        destination_path = resolve_workspace_path(destination)


        if not destination_path.exists():
            return error_result(
                "not_found",
                (
                    "Destination directory does not exist: "
                    f"{destination}"
                ),
            )


        if not destination_path.is_dir():
            return error_result(
                "not_a_directory",
                (
                    "Destination path is not a directory: "
                    f"{destination}"
                ),
            )


        if destination_path == workspace_root:
            return error_result(
                "protected_path",
                (
                    "The workspace root cannot be used as "
                    "an extraction destination."
                ),
            )


        try:
            next(destination_path.iterdir())

        except StopIteration:
            pass

        else:
            return error_result(
                "destination_not_empty",
                (
                    "Destination directory is not empty: "
                    f"{destination}"
                ),
            )


        # =====================================================================
        # Open ZIP Archive
        # =====================================================================


        with ZipFile(
            archive_path,
            mode="r",
        ) as zip_archive:

            archive_entries = zip_archive.infolist()


            # =================================================================
            # Archive Entry Count Limit
            # =================================================================


            if len(archive_entries) > MAX_ARCHIVE_ENTRIES:
                return error_result(
                    "too_many_archive_entries",
                    (
                        "Archive contains more than the maximum allowed "
                        f"{MAX_ARCHIVE_ENTRIES} entries."
                    ),
                )


            # =================================================================
            # Validate All Entries Before Extraction
            # =================================================================


            total_extracted_bytes = 0


            for entry in archive_entries:

                # -------------------------------------------------------------
                # Reject Absolute Archive Paths
                # -------------------------------------------------------------


                entry_path = Path(entry.filename)


                if entry_path.is_absolute():
                    return error_result(
                        "unsafe_archive_entry",
                        (
                            "Archive contains an unsafe absolute path: "
                            f"{entry.filename}"
                        ),
                    )


                # -------------------------------------------------------------
                # Resolve Final Extraction Path
                # -------------------------------------------------------------


                extracted_path = (
                    destination_path / entry.filename
                ).resolve()


                try:
                    extracted_path.relative_to(destination_path)

                except ValueError:
                    return error_result(
                        "unsafe_archive_entry",
                        (
                            "Archive entry escapes the destination "
                            f"directory: {entry.filename}"
                        ),
                    )


                # -------------------------------------------------------------
                # Reject Symbolic Links
                # -------------------------------------------------------------


                unix_mode = entry.external_attr >> 16


                if (unix_mode & 0o170000) == 0o120000:
                    return error_result(
                        "unsupported_archive_entry",
                        (
                            "Archive contains a symbolic link entry: "
                            f"{entry.filename}"
                        ),
                    )


                # -------------------------------------------------------------
                # Extracted Size Limit
                # -------------------------------------------------------------


                total_extracted_bytes += entry.file_size


                if total_extracted_bytes > MAX_EXTRACTED_BYTES:
                    return error_result(
                        "archive_too_large",
                        (
                            "Archive exceeds the maximum allowed extracted "
                            f"size of {MAX_EXTRACTED_BYTES} bytes."
                        ),
                    )


            # =================================================================
            # Extract Validated Entries
            # =================================================================


            extracted_files = 0

            extracted_directories = 0


            for entry in archive_entries:

                target_path = (
                    destination_path / entry.filename
                ).resolve()


                # -------------------------------------------------------------
                # Directory Entry
                # -------------------------------------------------------------


                if entry.is_dir():

                    target_path.mkdir(
                        parents=True,
                        exist_ok=True,
                    )

                    extracted_directories += 1

                    continue


                # -------------------------------------------------------------
                # Regular File Entry
                # -------------------------------------------------------------


                target_path.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )


                with zip_archive.open(
                    entry,
                    mode="r",
                ) as source_file:

                    with target_path.open(
                        mode="xb",
                    ) as destination_file:

                        shutil.copyfileobj(
                            source_file,
                            destination_file,
                        )


                extracted_files += 1


        # =====================================================================
        # Return Successful Result
        # =====================================================================


        return {
            "ok": True,
            "archive": archive,
            "destination": destination,
            "extracted_files": extracted_files,
            "extracted_directories": extracted_directories,
            "extracted_bytes": total_extracted_bytes,
            "extracted": True,
        }


    # =========================================================================
    # Invalid ZIP Archive
    # =========================================================================


    except BadZipFile:

        return error_result(
            "invalid_archive",
            "Unable to read ZIP archive.",
        )


    # =========================================================================
    # Workspace Security Error
    # =========================================================================


    except PathSecurityError as exc:

        return error_result(
            "path_security_error",
            str(exc),
        )


    # =========================================================================
    # Filesystem Error
    # =========================================================================


    except OSError:

        # ---------------------------------------------------------------------
        # Clean Partial Extraction
        # ---------------------------------------------------------------------


        if (
            destination_path is not None
            and destination_path.exists()
            and destination_path.is_dir()
        ):

            try:

                for child in destination_path.iterdir():

                    if child.is_dir():
                        shutil.rmtree(child)

                    else:
                        child.unlink()

            except OSError:
                pass


        return error_result(
            "filesystem_error",
            "Unable to extract ZIP archive.",
        )