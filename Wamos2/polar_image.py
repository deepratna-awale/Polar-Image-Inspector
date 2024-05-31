# https://www.yumpu.com/en/document/read/49205057/wamos-ii-manual

import io
from loguru import logger
import pathlib
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from scipy.interpolate import griddata
from PIL import PngImagePlugin, Image
import json

logger.add("Output/log.log", rotation="1 week")

class PolarImage:
    def __init__(self, file_path: str):
        """
        Initialize a PolarImage object.

        Args:
            file_path (str): The path to the image file.
        """

        self.file_path: pathlib.Path = pathlib.Path(file_path)
        self.image_size: int = 0
        self.header: dict = {}
        self.image_data = None
        self.eoh: int = None

        try:
            header_content, image_content = self._process_file()
        except Exception as e:
            logger.critical(f"Error processing file: {e}")
            return

        if header_content:
            self.header = self._process_header(header_content)
        else:
            logger.critical("Error reading the header. Did not find EOH Marker")
            return

        if image_content:
            self.image_data = self._process_image(image_content)
        else:
            logger.critical(
                "Error reading the image content. Check if EOH Marker was found."
            )
            return

        if self.image_data:
            self.image_array = self.get_image_array()
        else:
            logger.critical("Error Creating Image Array, could not find image data.")
            return

        logger.info(f"Processed {self.file_path.stem}")

    def _process_file(self):
        """
        Processes the file to separate header and image content.

        Returns:
            tuple: A tuple containing the header content and image content.
                Returns (None, None) if the EOH marker is not found.
        """
        try:
            with open(self.file_path, "rb") as file:
                content = file.read()
        except IOError as e:
            logger.critical(f"Error opening or reading the file: {e}")
            return None, None

        eoh_marker = b"EOH"
        eoh_index = content.find(eoh_marker)

        if eoh_index == -1:
            return None, None

        # Find the end of header (EOH) by looking for the line ending after the EOH marker
        eoh_end_index = eoh_index + content[eoh_index:].find(b"\r\n") + 2

        self.eoh = eoh_end_index

        header_content = content[: self.eoh]
        image_content = content[self.eoh :]

        return header_content, image_content

    def _process_header(self, header_content: bytes) -> dict:
        """
        Processes the header content and extracts key-value pairs.

        Args:
            header_content (bytes): The header content in bytes.

        Returns:
            dict: A dictionary containing the header information.
        """
        header_dict = {}
        desc_not_found = []

        # Split the header content by lines and remove the last empty line if exists
        header_lines = header_content.split(b"\r\n")[:-1]

        for line in header_lines:
            # Skip comment lines starting with 'CC' or '**'
            if line.startswith((b"CC", b"**")):
                continue

            try:
                text = line.decode("latin1")
                text = " ".join(text.split())  # Remove extra spaces
                key, value = text.split(
                    " ", maxsplit=1
                )  # Divide string into key and value

                if not value:  # Skip if value is empty
                    continue

                cc_index = value.find("CC")

                if cc_index != -1:  # If comment is found in the value
                    new_value = value[:cc_index].strip()
                    description = value[cc_index + 2 :].strip()
                    header_dict[key] = {
                        "value": self.auto_type(new_value),
                        "description": description,
                    }
                else:
                    desc_not_found.append(key)
                    header_dict[key] = {
                        "value": self.auto_type(value.strip()),
                        "description": "N/A",
                    }

            except ValueError as e:
                misc = line.decode("latin1").split(" ", maxsplit=1)
                logger.debug(f"Found no value, skipping: {misc}. Error: {e}")

        # Add the EOH value to the header dictionary
        header_dict["EOH"] = {"value": self.eoh, "description": "End of Header character position"}

        logger.debug(
            f"Could not find description for the following keys in Polar Image file: {desc_not_found}."
        )
        logger.debug("Header created successfully.")

        return header_dict

    def _process_image(self, image_content: bytes) -> bytes:
        """
        Processes the image content to extract the actual image data.

        Args:
            image_content (bytes): The image content in bytes.

        Returns:
            bytes: The extracted image data.
        """
        try:
            # Determine the size of the image
            self.image_size = self.get_image_size(image_content)
            logger.debug(f"Found image of size {self.image_size} bytes.")

            # Number of bytes describing the image size (can be adjusted if needed)
            chars_describing_image_bytes = 10

            # Extract the actual image data
            self.image_data = image_content[chars_describing_image_bytes:]
            return self.image_data

        except Exception as e:
            logger.critical(f"Error processing image content: {e}")
            return b""

    def get_image_size(self, image_content: bytes) -> int:
        """
        Determines the size of the image from the image content.

        Args:
            image_content (bytes): The image content in bytes.

        Returns:
            int: The size of the image.
        """
        try:
            # Determine the number of bytes used to describe the image size based on the "DABIT" value
            chars_describing_image_bytes = 10 if self.get("DABIT") == 12 else 6

            # Extract and return the image size
            image_size = int(
                image_content[:chars_describing_image_bytes].decode("latin1")
            )
            return image_size

        except ValueError as e:
            logger.critical(f"Error decoding image size: {e}")
            return 0
        except KeyError as e:
            logger.critical(f"Error accessing 'DABIT' value: {e}")
            return 0

    def describe(self, attribute: str) -> str:
        """
        Returns the description of a given attribute from the header.

        Args:
            attribute (str): The attribute whose description is to be retrieved.

        Returns:
            str: The description of the attribute, or None if not found.
        """
        attribute = attribute.upper()
        if not self.header:
            logger.warning("Header is not initialized.")
            return None

        try:
            return self.header[attribute]["description"]
        except KeyError:
            logger.exception(f"Attribute '{attribute}' not found in the header.")
            return None

    def get(self, attribute: str) -> any:
        """
        Retrieves the value of a given attribute from the header.

        Args:
            attribute (str): The attribute whose value is to be retrieved.

        Returns:
            any: The value of the attribute, or None if not found.
        """
        attribute = attribute.upper()
        if not self.header:
            logger.warning("Header is not initialized.")
            return None

        try:
            return self.header[attribute]["value"]
        except KeyError:
            logger.exception(f"Attribute '{attribute}' not found in the header.")
            return None

    def auto_type(self, string: str) -> any:
        """
        Tries to automatically convert a string to its correct data type.

        Args:
            string (str): The string to be converted.

        Returns:
            any: The converted value with its correct data type, or the original string if conversion fails.
        """
        # Attempt to convert to integer
        if string.isdigit():
            logger.debug(f'Converted "{string}" to type {type(int(string))}.')
            return int(string)

        # Attempt to convert to float
        try:
            float_val = float(string)
            logger.debug(f'Converted "{string}" to type {type(float_val)}.')
            return float_val
        except ValueError:
            pass

        # Attempt to convert to boolean
        if string.lower() in ["true", "false"]:
            bool_val = string.lower() == "true"
            logger.debug(f'Converted "{string}" to type {type(bool_val)}.')
            return bool_val

        # Return the original string if no conversion was possible
        logger.debug(f'Returning original string "{string}".')
        return string

    def get_image_array(self) -> np.ndarray:
        """
        Creates an image array from the image data based on the DABIT value.

        Returns:
            np.ndarray: The created image array.
        """
        try:
            no_of_samples_in_range = int(self.get("FIFO"))
            dabit_value = int(self.get("DABIT"))

            if dabit_value == 12:
                no_of_rays = self.image_size // (2 * no_of_samples_in_range)
                dtype = np.uint16
                mask = 0x0FFF
            elif dabit_value == 8:
                no_of_rays = self.image_size // no_of_samples_in_range
                dtype = np.uint8
                mask = None
            else:
                logger.error(f"Unsupported DABIT value: {dabit_value}")
                return np.array([])

            # Reshape the image data to form the image array
            image_array = (
                np.frombuffer(self.image_data, dtype=dtype)
                .copy()
                .reshape((no_of_rays, no_of_samples_in_range))
            )

            # Apply mask if needed
            if mask is not None:
                image_array &= mask

            # Set the first byte of each ray to zero for 8-bit data
            if dabit_value == 8:
                image_array[:, 0] = 0

            logger.info(f"Created image array of size {image_array.shape}")
            return image_array

        except Exception as e:
            logger.critical(f"Error creating image array: {e}")
            return np.array([])

    def interpolate(self, method="cubic"):
        """
        Interpolates the image data to a finer grid resolution.
        """
        try:
            # Original grid dimensions
            data = self.image_array
            num_rows, num_cols = data.shape

            # Original grid points
            original_x = np.linspace(0, 1, num_cols)
            original_y = np.linspace(0, 1, num_rows)

            # Target grid - increase resolution
            fine_x = np.linspace(0, 1, num_cols * 2)
            fine_y = np.linspace(0, 1, num_rows * 2)

            # Create meshgrids for original and fine resolutions
            original_x_mesh, original_y_mesh = np.meshgrid(original_x, original_y)
            fine_x_mesh, fine_y_mesh = np.meshgrid(fine_x, fine_y)

            # Interpolate data to the finer grid
            fine_data = griddata(
                (original_x_mesh.ravel(), original_y_mesh.ravel()),
                data.ravel(),
                (fine_x_mesh, fine_y_mesh),
                method=method,
            )  # Can try 'linear' or 'nearest'
            self.image_array = fine_data

        except Exception as e:
            logger.critical(f"Error interpolating image data: {e}")

    def render(
        self, orient: bool = True, toggle_direction: bool = True, cmap: str = "Greys_r"
    ):
        """
        Renders the polar image with optional orientation and direction settings.

        Args:
            orient (bool): Whether to orient the image based on the header information.
            toggle_direction (bool): Whether to toggle the direction of the plot.
            cmap (str): The colormap to use for rendering.

        Returns:
            matplotlib.figure.Figure: The rendered polar image figure.
        """
        sampling_frequency = int(self.get("SFREQ"))
        sampling_delay_range = int(self.get("SDRNG"))

        if sampling_frequency == 40:
            pixels_to_omit = int(np.ceil(sampling_delay_range / 3.75)) * 2
        else:
            c = 3e8
            meters_per_pixel = c / (2 * sampling_frequency * 1e6)
            pixels_to_omit = int(np.ceil(sampling_delay_range / meters_per_pixel)) * 2

        if self.get('DABIT') == 12:
            HIGHEST_BRIGHTNESS = 4095
        else:
            HIGHEST_BRIGHTNESS = 255

        additional_columns = pixels_to_omit
        new_columns = np.full(
            (self.image_array.shape[0], additional_columns), HIGHEST_BRIGHTNESS
        )
        self.image_array = np.concatenate((new_columns, self.image_array), axis=1)

        rays_angles = np.linspace(
            0, (2 * np.pi), self.image_array.shape[0], endpoint=True
        )
        pixel_positions = np.arange(0, self.image_array.shape[1])

        theta, r = np.meshgrid(rays_angles, pixel_positions)

        plt.figure(figsize=(4, 4))
        fig, ax = plt.subplots(subplot_kw={"projection": "polar"})
        ax.pcolormesh(
            theta,
            r,
            self.image_array.T,
            cmap=cmap,
            norm=Normalize(0, 4095),
            shading="gouraud",
        )

        ax.grid(False)
        ax.set_yticklabels([])
        ax.set_xticklabels([])

        if toggle_direction:
            ax.set_theta_direction(-1)
        else:
            ax.set_theta_direction(1)

        if orient:
            bo2ra = np.deg2rad(int(2 * self.get("BO2RA")))
            ax.set_theta_offset(-bo2ra)
        else:
            ax.set_theta_offset((np.pi / 2))

        plt.close(fig)
        return fig

    def saveto(self, output_path=None, file_extension: str = ".png"):
        """
        Saves the rendered polar image to a file.

        Args:
            output_path (str): The path where the image should be saved. If None, a default path will be used.
            file_extension (str): The file extension for the saved image.

        Returns:
            str: The path where the image was saved.
        """
        if not output_path:
            new_path = self.file_path.relative_to(self.file_path.parent.parent)
            output_path = pathlib.Path("Output", new_path).with_suffix(file_extension)
            logger.info(f"Saving to {output_path}")
        else:
            output_path = pathlib.Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.render(orient=True, toggle_direction=False).savefig(
            output_path, dpi=300, bbox_inches="tight"
        )

        return str(output_path)

    def save_with_metadata(self, output_path=None, file_extension: str = ".png"):
        """
        Saves the rendered polar image to a file with embedded metadata.

        Args:
            output_path (str): The path where the image should be saved. If None, a default path will be used.
            file_extension (str): The file extension for the saved image.

        """
        if not output_path:
            new_path = self.file_path.relative_to(self.file_path.parent.parent)
            output_path = pathlib.Path("Output", new_path).with_suffix(file_extension)
            logger.info(f"Saving to {output_path}")
        else:
            output_path = pathlib.Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig = self.render(orient=True, toggle_direction=False)
        img_data = io.BytesIO()

        fig.savefig(img_data, format=file_extension[1:], dpi=300, bbox_inches="tight")

        plt.close(fig)

        img_data.seek(0)

        # Load the image data into PIL
        img = Image.open(img_data)

        # Prepare a PngInfo object to store textual information
        metadata = PngImagePlugin.PngInfo()

        json_data = json.dumps(self.header, indent=4)
        # Add JSON data to the PngInfo object
        metadata.add_text("json_data", json_data)

        # Save the image with the embedded JSON data
        img.save(output_path, pnginfo=metadata)
