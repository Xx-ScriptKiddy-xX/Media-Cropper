# Media Cropper App
<img width="600" height="600" alt="Cropper" src="https://github.com/user-attachments/assets/8194eedf-09ad-4655-97d7-f4a801b8182b" />

**Image & Video Cropper App** is a desktop application for previewing, cropping, and exporting **images and videos** with precise control. Built with **Python, PyQt5, OpenCV, and FFmpeg**, it provides real-time previews, interactive crop tools, and high-quality exports.

---

## Key Features

- **Image & Video Support** – Works with `png, jpg, jpeg, mp4, mov, mkv`.  
- **Live Preview** – Real-time image and video preview with looping playback.  
- **Interactive Crop Box** – Drag and reposition the crop area visually.  
- **Aspect Ratio Presets** – Includes `1:1, 16:9, 9:16, 3:2, 2:1, 5:3` and more.  
- **Manual Offset Controls** – Fine-tune crop position using X/Y offset inputs.  
- **Folder & File Import** – Import single files or entire folders.  
- **High-Quality Export** – Preserves resolution and quality for both images and videos.  
- **GPU Acceleration** – Uses CUDA with FFmpeg when available for faster video processing.  
- **Config Saving** – Automatically saves last settings and export directory.  
- **Custom Export Directory** – Choose where cropped files are saved.

---

## Built With

- **Python**  
- **PyQt5** – GUI framework  
- **OpenCV** – Image and video processing  
- **FFmpeg** – Video cropping and encoding  
- **JSON** – Configuration storage

---

## Usage

1. Launch the application.  
2. Import files or select a folder.  
3. Choose an image or video from the list.  
4. Select an aspect ratio.  
5. Adjust the crop box by dragging or using offset controls.  
6. Click **Export Crop** to save the result.

<img width="388" height="388" alt="Screenshot 2026-02-21 225531" src="https://github.com/user-attachments/assets/73b95cd9-f845-4e88-9fbd-5055ca2f3cc9" />



---

## Notes

- Cropped files are saved as `cropped_filename.ext`.  
- Videos are processed using FFmpeg for high-quality output.  
- GPU acceleration is used when supported.  
- Configuration is stored in `Configs/Cc.json`.  
- Both the compiled executable and source code are available in the repository and the **Releases** tab.

---

## License

This project is open source under the **MIT License**.
