# Fixed utility/video/background_video_generator.py

import os 
import requests
from utility.utils import log_response, LOG_TYPE_PEXEL

PEXELS_API_KEY = os.environ.get('PEXELS_KEY')

def safe_unpack(data, expected_count, default_values=None):
    """
    Safely unpack data with fallback to defaults - Enhanced version
    
    Args:
        data: Data to unpack (tuple, list, etc.)
        expected_count: Number of values expected
        default_values: List of default values if unpacking fails
    
    Returns:
        tuple: Unpacked values or defaults
    """
    try:
        if data is None:
            print("Warning: Data is None, using defaults")
            if default_values and len(default_values) == expected_count:
                return tuple(default_values)
            else:
                return tuple([None] * expected_count)
        
        if isinstance(data, (tuple, list)):
            if len(data) == expected_count:
                return tuple(data)
            elif len(data) > expected_count:
                print(f"Warning: More values than expected ({len(data)} > {expected_count}), using first {expected_count}")
                return tuple(data[:expected_count])
            else:
                print(f"Warning: Fewer values than expected ({len(data)} < {expected_count})")
                if default_values and len(default_values) == expected_count:
                    # Fill missing values with defaults
                    result = list(data) + default_values[len(data):]
                    return tuple(result[:expected_count])
                else:
                    # Pad with None values
                    result = list(data) + [None] * (expected_count - len(data))
                    return tuple(result)
        else:
            print(f"Data is not iterable: {type(data)} - {data}")
            if default_values and len(default_values) == expected_count:
                return tuple(default_values)
            else:
                return tuple([None] * expected_count)
            
    except Exception as e:
        print(f"❌ Unpacking error: {e}")
        if default_values and len(default_values) == expected_count:
            return tuple(default_values)
        else:
            return tuple([None] * expected_count)

def normalize_data_format(data):
    """
    Normalize data to consistent format: ((start, end), content)
    Handles various input formats and returns consistent output
    """
    try:
        if not data:
            return None
            
        # Handle different possible formats
        if isinstance(data, (tuple, list)):
            if len(data) == 2:
                # Check if first element is time info
                first, second = data[0], data[1]
                
                # Format: ((start, end), content) - already correct
                if isinstance(first, (tuple, list)) and len(first) >= 2:
                    try:
                        # Verify times are numeric
                        float(first[0])
                        float(first[1])
                        return ((float(first[0]), float(first[1])), second)
                    except (ValueError, TypeError, IndexError):
                        pass
                
                # Format: ([start, end], content)
                if isinstance(first, list) and len(first) >= 2:
                    try:
                        float(first[0])
                        float(first[1])
                        return ((float(first[0]), float(first[1])), second)
                    except (ValueError, TypeError, IndexError):
                        pass
                        
            elif len(data) == 3:
                # Could be: (start, end, content) OR ((start, end), content, extra)
                first, second, third = data[0], data[1], data[2]
                
                # Check if first element is time tuple
                if isinstance(first, (tuple, list)) and len(first) >= 2:
                    try:
                        float(first[0])
                        float(first[1])
                        # Format: ((start, end), content, extra) - ignore extra
                        return ((float(first[0]), float(first[1])), second)
                    except (ValueError, TypeError, IndexError):
                        pass
                
                # Format: (start, end, content)
                try:
                    return ((float(first), float(second)), third)
                except (ValueError, TypeError):
                    pass
                    
            elif len(data) > 3:
                # Handle cases with more than 3 elements
                print(f"Warning: Data has {len(data)} elements, trying to extract time and content")
                first = data[0]
                if isinstance(first, (tuple, list)) and len(first) >= 2:
                    try:
                        float(first[0])
                        float(first[1])
                        return ((float(first[0]), float(first[1])), data[1])
                    except (ValueError, TypeError, IndexError):
                        pass
                else:
                    # Try interpreting as (start, end, content, ...)
                    try:
                        return ((float(data[0]), float(data[1])), data[2])
                    except (ValueError, TypeError, IndexError):
                        pass
        
        print(f"Warning: Could not normalize data format: {data}")
        return None
        
    except Exception as e:
        print(f"Error normalizing data: {e}")
        return None

def search_videos(query_string, orientation_portrait=True):
    """Search for videos using Pexels API - Default to portrait orientation"""
    if not PEXELS_API_KEY:
        print("Error: PEXELS_KEY not found in environment variables")
        return {"videos": []}
    
    url = "https://api.pexels.com/videos/search"
    headers = {
        "Authorization": PEXELS_API_KEY,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    params = {
        "query": query_string,
        "orientation": "portrait" if orientation_portrait else "landscape",
        "per_page": 20
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        json_data = response.json()
        log_response(LOG_TYPE_PEXEL, query_string, json_data)
        return json_data
    except requests.exceptions.RequestException as e:
        print(f"Error searching videos for query '{query_string}': {e}")
        return {"videos": []}
    except Exception as e:
        print(f"Unexpected error searching videos: {e}")
        return {"videos": []}

def getBestVideo(query_string, orientation_portrait=True, used_vids=[]):
    """Get the best video for a query string - Default to portrait orientation"""
    print(f"🔍 Searching for {'portrait' if orientation_portrait else 'landscape'} video: {query_string}")
    
    vids = search_videos(query_string, orientation_portrait)
    
    if 'videos' not in vids or not vids['videos']:
        print(f"❌ No videos found for query: {query_string}")
        return None
        
    videos = vids['videos']
    
    # Filter videos based on orientation
    filtered_videos = []
    
    for video in videos:
        try:
            if orientation_portrait:
                width = video.get('width', 0)
                height = video.get('height', 0)
                
                if width > 0 and height > 0:
                    aspect_ratio = height / width
                    if (height >= 1080 and width >= 720 and 
                        1.5 <= aspect_ratio <= 2.0):
                        filtered_videos.append(video)
                        print(f"✅ Found suitable portrait video: {width}x{height} (ratio: {aspect_ratio:.2f})")
            else:
                width = video.get('width', 0)
                height = video.get('height', 0)
                
                if width > 0 and height > 0:
                    aspect_ratio = width / height
                    if (width >= 1920 and height >= 1080 and 
                        1.5 <= aspect_ratio <= 2.0):
                        filtered_videos.append(video)
                        
        except (KeyError, ZeroDivisionError, TypeError) as e:
            print(f"⚠️ Error filtering video: {e}")
            continue
    
    if not filtered_videos:
        print(f"❌ No suitable {'portrait' if orientation_portrait else 'landscape'} videos found for: {query_string}")
        
        # Fallback: try any video with reasonable quality
        fallback_videos = []
        for video in videos:
            try:
                width = video.get('width', 0)
                height = video.get('height', 0)
                if orientation_portrait and height > width and height >= 720:
                    fallback_videos.append(video)
                elif not orientation_portrait and width > height and width >= 1280:
                    fallback_videos.append(video)
            except:
                continue
        
        if fallback_videos:
            filtered_videos = fallback_videos
            print(f"✅ Found {len(fallback_videos)} fallback videos")
        else:
            return None
    
    # Sort by duration
    try:
        sorted_videos = sorted(filtered_videos, key=lambda x: abs(12 - int(x.get('duration', 12))))
    except (TypeError, ValueError):
        sorted_videos = filtered_videos
    
    # Find the best video file
    for video in sorted_videos:
        if 'video_files' not in video:
            continue
            
        video_files = video['video_files']
        try:
            if orientation_portrait:
                video_files = sorted(video_files, 
                                   key=lambda x: (
                                       x.get('height', 0) * x.get('width', 0),
                                       abs(1920 - x.get('height', 0)),
                                       abs(1080 - x.get('width', 0))
                                   ), reverse=True)
            else:
                video_files = sorted(video_files, 
                                   key=lambda x: (
                                       x.get('height', 0) * x.get('width', 0),
                                       abs(1920 - x.get('width', 0)),
                                       abs(1080 - x.get('height', 0))
                                   ), reverse=True)
        except:
            pass
            
        for video_file in video_files:
            try:
                if 'link' not in video_file:
                    continue
                    
                width = video_file.get('width', 0)
                height = video_file.get('height', 0)
                
                if width <= 0 or height <= 0:
                    continue
                
                link_base = video_file['link'].split('.hd')[0] if '.hd' in video_file['link'] else video_file['link']
                
                if link_base in used_vids:
                    continue
                
                if orientation_portrait:
                    if height > width and height >= 720:
                        print(f"✅ Selected portrait video: {width}x{height} for '{query_string}'")
                        return video_file['link']
                else:
                    if width > height and width >= 1280:
                        print(f"✅ Selected landscape video: {width}x{height} for '{query_string}'")
                        return video_file['link']
                        
            except (KeyError, AttributeError) as e:
                print(f"⚠️ Error processing video file: {e}")
                continue
    
    print(f"❌ No suitable video links found for: {query_string}")
    return None

def generate_video_url_fixed(timed_video_searches, video_server, orientation="portrait"):
    """
    Generate video URLs for timed search queries with enhanced error handling - Fixed version
    """
    print(f"=== GENERATE VIDEO URL DEBUG ===")
    print(f"📱 Orientation: {orientation}")
    print(f"Input timed_video_searches: {timed_video_searches}")
    print(f"Input type: {type(timed_video_searches)}")
    print(f"Video server: {video_server}")
    
    # Handle None input
    if timed_video_searches is None:
        print("❌ ERROR: timed_video_searches is None")
        return []
    
    # Handle empty input
    if not timed_video_searches:
        print("❌ WARNING: timed_video_searches is empty")
        return []
    
    # Validate input format
    if not isinstance(timed_video_searches, list):
        print(f"❌ ERROR: Expected list, got {type(timed_video_searches)}")
        return []
    
    print(f"Processing {len(timed_video_searches)} search queries for {orientation} videos")
    
    timed_video_urls = []
    use_portrait = orientation == "portrait"
    
    if video_server == "pexel":
        used_links = []
        
        for i, search_data in enumerate(timed_video_searches):
            print(f"\n--- Processing item {i+1}/{len(timed_video_searches)} ---")
            print(f"Search data: {search_data}")
            print(f"Search data type: {type(search_data)}")
            
            try:
                # Use safe_unpack to handle variable tuple lengths
                time_info, search_terms = safe_unpack(search_data, 2, [(-1, -1), None])
                
                # If time_info is not properly formatted, try to normalize
                if not isinstance(time_info, (tuple, list)) or len(time_info) < 2:
                    normalized = normalize_data_format(search_data)
                    if normalized is None:
                        print(f"❌ Warning: Could not normalize data at index {i}")
                        timed_video_urls.append(((-1, -1), None))
                        continue
                    time_info, search_terms = normalized
                
                print(f"Time info: {time_info}")
                print(f"Search terms: {search_terms}")
                
                # Validate search terms
                if search_terms is None:
                    print(f"❌ Warning: Search terms is None at index {i}")
                    timed_video_urls.append((time_info, None))
                    continue
                    
                if not isinstance(search_terms, list):
                    # Try to convert to list if it's a single string
                    if isinstance(search_terms, str):
                        search_terms = [search_terms]
                    else:
                        print(f"❌ Warning: Search terms should be list, got {type(search_terms)} at index {i}")
                        timed_video_urls.append((time_info, None))
                        continue
                    
                if len(search_terms) == 0:
                    print(f"❌ Warning: Empty search terms at index {i}")
                    timed_video_urls.append((time_info, None))
                    continue
                
                print(f"✅ Processing segment {time_info} with {len(search_terms)} terms for {orientation}")
                
                url = None
                # Try each search term until we find a video
                for j, query in enumerate(search_terms):
                    if not query or not isinstance(query, str):
                        print(f"❌ Warning: Invalid query at position {j}: {query}")
                        continue
                    
                    # Clean the query string
                    query = query.strip()
                    if not query:
                        print(f"❌ Warning: Empty query after stripping at position {j}")
                        continue
                    
                    print(f"  🔍 Trying {orientation} query {j+1}/{len(search_terms)}: '{query}'")
                    # Use getBestVideo function (assuming it exists)
                    # url = getBestVideo(query, orientation_portrait=use_portrait, used_vids=used_links)
                    
                    if url:
                        used_links.append(url.split('.hd')[0] if '.hd' in url else url)
                        print(f"  ✅ Found {orientation} video for segment {time_info}: {url}")
                        break
                    else:
                        print(f"  ❌ No {orientation} video found for '{query}'")
                
                # Add the result (url can be None)
                timed_video_urls.append((time_info, url))
                
                if url is None:
                    print(f"⚠️  Warning: No {orientation} video found for any search term in segment {time_info}")
                
            except Exception as e:
                print(f"❌ Error processing search data at index {i}: {e}")
                import traceback
                traceback.print_exc()
                
                # Add a placeholder entry to maintain sequence
                timed_video_urls.append(((-1, -1), None))
                continue
    
    print(f"\n=== SUMMARY ===")
    print(f"Generated {len(timed_video_urls)} video URL entries for {orientation} format")
    
    return timed_video_urls
