import os 
import requests
from utility.utils import log_response, LOG_TYPE_PEXEL

PEXELS_API_KEY = os.environ.get('PEXELS_KEY')

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
        "per_page": 20  # Increased to find more portrait videos
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
                # For portrait (9:16): height should be significantly greater than width
                # Target: 1080x1920 or similar ratios
                width = video.get('width', 0)
                height = video.get('height', 0)
                
                if width > 0 and height > 0:
                    aspect_ratio = height / width
                    # Accept aspect ratios between 1.5 and 2.0 (covers 9:16 = 1.78)
                    if (height >= 1080 and width >= 720 and 
                        1.5 <= aspect_ratio <= 2.0):
                        filtered_videos.append(video)
                        print(f"✅ Found suitable portrait video: {width}x{height} (ratio: {aspect_ratio:.2f})")
            else:
                # For landscape: width >= height, aspect ratio close to 16:9
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
        print(f"🔄 Trying fallback search for any quality video...")
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
    
    # Sort by duration (prefer videos around 10-15 seconds for short content)
    try:
        sorted_videos = sorted(filtered_videos, key=lambda x: abs(12 - int(x.get('duration', 12))))
    except (TypeError, ValueError):
        sorted_videos = filtered_videos
    
    # Find the best video file
    for video in sorted_videos:
        if 'video_files' not in video:
            continue
            
        # Sort video files by quality (highest first)
        video_files = video['video_files']
        try:
            if orientation_portrait:
                # For portrait: prefer 1080x1920, then other high-quality portrait formats
                video_files = sorted(video_files, 
                                   key=lambda x: (
                                       x.get('height', 0) * x.get('width', 0),  # Total pixels
                                       abs(1920 - x.get('height', 0)),  # Closeness to 1920 height
                                       abs(1080 - x.get('width', 0))    # Closeness to 1080 width
                                   ), reverse=True)
            else:
                # For landscape: prefer 1920x1080
                video_files = sorted(video_files, 
                                   key=lambda x: (
                                       x.get('height', 0) * x.get('width', 0),  # Total pixels
                                       abs(1920 - x.get('width', 0)),   # Closeness to 1920 width
                                       abs(1080 - x.get('height', 0))   # Closeness to 1080 height
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
                    # Accept any portrait video with decent quality
                    if height > width and height >= 720:
                        print(f"✅ Selected portrait video: {width}x{height} for '{query_string}'")
                        print(f"📹 URL: {video_file['link']}")
                        return video_file['link']
                else:
                    # Accept any landscape video with decent quality
                    if width > height and width >= 1280:
                        print(f"✅ Selected landscape video: {width}x{height} for '{query_string}'")
                        print(f"📹 URL: {video_file['link']}")
                        return video_file['link']
                        
            except (KeyError, AttributeError) as e:
                print(f"⚠️ Error processing video file: {e}")
                continue
    
    print(f"❌ No suitable video links found for: {query_string}")
    return None

def generate_video_url(timed_video_searches, video_server, orientation="portrait"):
    """Generate video URLs for timed search queries with enhanced error handling
    
    Args:
        timed_video_searches: List of timed search queries
        video_server: Video service to use ("pexel" or "stable_diffusion")
        orientation: "portrait" for 9:16 or "landscape" for 16:9
    """
    print(f"=== GENERATE VIDEO URL DEBUG ===")
    print(f"📱 Orientation: {orientation} ({'9:16 portrait' if orientation == 'portrait' else '16:9 landscape'})")
    print(f"Input timed_video_searches: {timed_video_searches}")
    print(f"Input type: {type(timed_video_searches)}")
    print(f"Video server: {video_server}")
    
    # Handle None input
    if timed_video_searches is None:
        print("❌ ERROR: timed_video_searches is None")
        print("This suggests the function that generates search queries failed.")
        print("Please check the function that calls generate_video_url()")
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
                # Validate search data format
                if not isinstance(search_data, list):
                    print(f"❌ Warning: Expected list, got {type(search_data)} at index {i}")
                    timed_video_urls.append([[-1, -1], None])
                    continue
                    
                if len(search_data) != 2:
                    print(f"❌ Warning: Expected 2 elements, got {len(search_data)} at index {i}")
                    timed_video_urls.append([[-1, -1], None])
                    continue
                
                time_segment, search_terms = search_data
                print(f"Time segment: {time_segment}")
                print(f"Search terms: {search_terms}")
                
                # Validate time segment
                if not isinstance(time_segment, list) or len(time_segment) != 2:
                    print(f"❌ Warning: Invalid time segment at index {i}: {time_segment}")
                    timed_video_urls.append([[-1, -1], None])
                    continue
                
                t1, t2 = time_segment
                
                # Ensure time values are numeric
                try:
                    t1, t2 = float(t1), float(t2)
                except (ValueError, TypeError):
                    print(f"❌ Warning: Non-numeric time values at index {i}: [{t1}, {t2}]")
                    timed_video_urls.append([[-1, -1], None])
                    continue
                
                # Validate search terms
                if not isinstance(search_terms, list):
                    print(f"❌ Warning: Search terms should be list, got {type(search_terms)} at index {i}")
                    timed_video_urls.append([[t1, t2], None])
                    continue
                    
                if len(search_terms) == 0:
                    print(f"❌ Warning: Empty search terms at index {i}")
                    timed_video_urls.append([[t1, t2], None])
                    continue
                
                print(f"✅ Processing segment [{t1}, {t2}] with {len(search_terms)} terms for {orientation}")
                
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
                    url = getBestVideo(query, orientation_portrait=use_portrait, used_vids=used_links)
                    
                    if url:
                        used_links.append(url.split('.hd')[0] if '.hd' in url else url)
                        print(f"  ✅ Found {orientation} video for segment [{t1}, {t2}]: {url}")
                        break
                    else:
                        print(f"  ❌ No {orientation} video found for '{query}'")
                
                # Add the result (url can be None)
                timed_video_urls.append([[t1, t2], url])
                
                if url is None:
                    print(f"⚠️  Warning: No {orientation} video found for any search term in segment [{t1}, {t2}]")
                
            except Exception as e:
                print(f"❌ Error processing search data at index {i}: {e}")
                print(f"Error type: {type(e)}")
                import traceback
                traceback.print_exc()
                
                # Add a placeholder entry to maintain sequence
                try:
                    if isinstance(search_data, list) and len(search_data) >= 1:
                        if isinstance(search_data[0], list) and len(search_data[0]) >= 2:
                            timed_video_urls.append([search_data[0], None])
                        else:
                            timed_video_urls.append([[-1, -1], None])
                    else:
                        timed_video_urls.append([[-1, -1], None])
                except:
                    timed_video_urls.append([[-1, -1], None])
                continue
        
    elif video_server == "stable_diffusion":
        print("Using stable_diffusion video server")
        try:
            # Check if function exists
            if 'get_images_for_video' in globals():
                timed_video_urls = get_images_for_video(timed_video_searches)
            else:
                print("❌ Error: get_images_for_video function not defined")
                return []
        except Exception as e:
            print(f"❌ Error with stable_diffusion: {e}")
            import traceback
            traceback.print_exc()
            return []
    else:
        print(f"❌ Error: Unknown video server '{video_server}'")
        return []
    
    print(f"\n=== SUMMARY ===")
    print(f"Generated {len(timed_video_urls)} video URL entries for {orientation} format")
    
    # Debug output
    successful_urls = sum(1 for entry in timed_video_urls if len(entry) >= 2 and entry[1] is not None)
    failed_urls = len(timed_video_urls) - successful_urls
    
    print(f"✅ Successful {orientation} video matches: {successful_urls}")
    print(f"❌ Failed video matches: {failed_urls}")
    print(f"📊 Success rate: {successful_urls/len(timed_video_urls)*100:.1f}%" if timed_video_urls else "0%")
    
    # Show first few results for debugging
    print(f"\nFirst 3 results:")
    for i, entry in enumerate(timed_video_urls[:3]):
        status = "✅" if len(entry) >= 2 and entry[1] else "❌"
        print(f"  {i+1}. {status} {entry}")
    
    if len(timed_video_urls) > 3:
        print(f"  ... and {len(timed_video_urls) - 3} more")
    
    return timed_video_urls

def validate_search_input(timed_video_searches):
    """Validate and analyze the input format for debugging"""
    print("=== INPUT VALIDATION ===")
    
    if timed_video_searches is None:
        print("❌ Input is None - check the calling function")
        return False
    
    if not isinstance(timed_video_searches, list):
        print(f"❌ Input should be list, got {type(timed_video_searches)}")
        return False
    
    if len(timed_video_searches) == 0:
        print("⚠️  Input list is empty")
        return False
    
    print(f"✅ Input is a list with {len(timed_video_searches)} items")
    
    # Check format of first few items
    for i, item in enumerate(timed_video_searches[:3]):
        print(f"\nItem {i+1}:")
        print(f"  Type: {type(item)}")
        print(f"  Value: {item}")
        
        if isinstance(item, list) and len(item) == 2:
            time_seg, terms = item
            print(f"  Time segment: {time_seg} (type: {type(time_seg)})")
            print(f"  Search terms: {terms} (type: {type(terms)})")
            
            if isinstance(terms, list):
                print(f"    Terms count: {len(terms)}")
                if terms:
                    print(f"    First term: '{terms[0]}' (type: {type(terms[0])})")
        else:
            print(f"  ❌ Invalid format - should be [time_segment, search_terms]")
    
    return True
def process_background_video_fixed(background_video_data):
    """
    Fixed version for processing background video data
    """
    for i, video_data in enumerate(background_video_data):
        try:
            # Handle different formats
            if isinstance(video_data, (tuple, list)):
                if len(video_data) == 2:
                    time_info, video_url = video_data
                elif len(video_data) > 2:
                    time_info, video_url = video_data[0], video_data[1]
                    print(f"Warning: Video data {i} has extra elements: {video_data[2:]}")
                else:
                    print(f"❌ Invalid video data format at {i}: {video_data}")
                    continue
                    
                # Further validate time_info
                if isinstance(time_info, (tuple, list)) and len(time_info) == 2:
                    t1, t2 = time_info
                    print(f"Processing video segment {i}: {t1}s - {t2}s")
                else:
                    print(f"❌ Invalid time format at {i}: {time_info}")
                    continue
                    
        except ValueError as e:
            print(f"❌ Error unpacking video data {i}: {e}")
            print(f"Data: {video_data}")
            continue
# Enhanced debugging function
def debug_video_search(timed_video_searches, orientation="portrait"):
    """Enhanced debug function to test video search"""
    print("\n" + "="*50)
    print(f"=== ENHANCED DEBUG: {orientation.upper()} Video Search Analysis ===")
    print("="*50)
    
    # First validate input
    if not validate_search_input(timed_video_searches):
        print("❌ Input validation failed - cannot proceed with debug")
        return
    
    print(f"\n🔍 Analyzing {len(timed_video_searches)} search queries for {orientation} videos...")
    
    # Test API key
    if not PEXELS_API_KEY:
        print("❌ CRITICAL: PEXELS_API_KEY not found!")
        print("Please set the PEXELS_KEY environment variable")
        return
    else:
        print("✅ PEXELS_API_KEY found")
    
    # Test a few queries
    test_count = min(3, len(timed_video_searches))
    print(f"\n🧪 Testing first {test_count} queries for {orientation} format:")
    
    use_portrait = orientation == "portrait"
    
    for i in range(test_count):
        search_data = timed_video_searches[i]
        print(f"\n--- Test {i+1} ---")
        
        try:
            if isinstance(search_data, list) and len(search_data) >= 2:
                time_segment, search_terms = search_data
                print(f"Time: {time_segment}")
                print(f"Terms: {search_terms}")
                
                if isinstance(search_terms, list) and len(search_terms) > 0:
                    # Test first search term
                    first_term = search_terms[0]
                    if first_term and isinstance(first_term, str):
                        print(f"Testing '{first_term}' for {orientation}...")
                        result = getBestVideo(first_term, orientation_portrait=use_portrait, used_vids=[])
                        print(f"Result: {'✅ Found' if result else '❌ Not found'}")
                        if result:
                            print(f"URL: {result}")
                    else:
                        print(f"❌ Invalid first term: {first_term}")
                else:
                    print("❌ No valid search terms")
            else:
                print(f"❌ Invalid search data format: {search_data}")
        
        except Exception as e:
            print(f"❌ Error during test: {e}")
    
    print("\n" + "="*50)
    print("=== END ENHANCED DEBUG ===")
    print("="*50)
def safe_unpack(data, expected_count, default_values=None):
    """
    Safely unpack data with fallback to defaults
    
    Args:
        data: Data to unpack (tuple, list, etc.)
        expected_count: Number of values expected
        default_values: List of default values if unpacking fails
    
    Returns:
        tuple: Unpacked values or defaults
    """
    try:
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
                    raise ValueError(f"Cannot unpack {len(data)} values into {expected_count} variables")
        else:
            raise ValueError(f"Data is not iterable: {type(data)}")
            
    except Exception as e:
        print(f"❌ Unpacking error: {e}")
        if default_values and len(default_values) == expected_count:
            return tuple(default_values)
        else:
            raise
