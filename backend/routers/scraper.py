"""
Scraper router — uses Google Places to find businesses and
Hunter.io (or free web scraper as fallback) to find HR emails.
"""
import asyncio
import os
from datetime import datetime
from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db, SessionLocal
from models import Lead, ScrapeJob
from services.google_places_service import search_businesses, GOOGLE_CATEGORIES

router = APIRouter()

# In-memory set of job IDs that have been requested to cancel
_cancel_requested: set[int] = set()

STATE_CITIES: dict[str, list[str]] = {
    # ── United States ──────────────────────────────────────────────────────────
    "AL": ["Birmingham","Montgomery","Huntsville","Mobile","Tuscaloosa","Hoover","Auburn","Dothan","Decatur","Madison","Gadsden","Florence","Anniston","Gulf Shores","Orange Beach","Prattville","Vestavia Hills","Phenix City"],
    "AK": ["Anchorage","Fairbanks","Juneau","Sitka","Ketchikan","Wasilla","Kenai","Kodiak","Bethel","Palmer","Skagway","Homer","Valdez","Seward","Soldotna"],
    "AZ": ["Phoenix","Tucson","Mesa","Chandler","Scottsdale","Glendale","Gilbert","Tempe","Peoria","Surprise","Yuma","Flagstaff","Goodyear","Avondale","Sedona","Prescott","Lake Havasu City","Kingman","Bullhead City","Show Low","Sierra Vista","Casa Grande","Maricopa"],
    "AR": ["Little Rock","Fayetteville","Fort Smith","Springdale","Jonesboro","Conway","Rogers","North Little Rock","Pine Bluff","Bentonville","Hot Springs","Texarkana","Sherwood","Jacksonville","Russellville","Bella Vista","West Memphis","Eureka Springs"],
    "CA": ["Los Angeles","San Diego","San Jose","San Francisco","Fresno","Sacramento","Long Beach","Oakland","Bakersfield","Anaheim","Santa Ana","Riverside","Stockton","Irvine","Chula Vista","Fremont","San Bernardino","Modesto","Fontana","Moreno Valley","Glendale","Oxnard","Huntington Beach","Santa Clarita","Garden Grove","Santa Rosa","Oceanside","Rancho Cucamonga","Ontario","Lancaster","Elk Grove","Palmdale","Corona","Salinas","Pomona","Torrance","Sunnyvale","Escondido","Pasadena","Fullerton","Hayward","Temecula","Visalia","Simi Valley","Concord","Roseville","Santa Clara","Victorville","Thousand Oaks","El Monte","Murrieta","Vallejo","Berkeley","Carlsbad","Downey","Costa Mesa","Inglewood","Ventura","West Covina","Norwalk","Antioch","Santa Barbara","Chico","El Cajon","Rialto","Richmond","Burbank","Daly City","Santa Maria","Westminster","Clovis","Napa","Palm Springs","Carmel","Monterey","Santa Cruz","Laguna Beach","Newport Beach","Malibu","Beverly Hills","Santa Monica","Big Sur","Sonoma","Lake Tahoe","South Lake Tahoe"],
    "CO": ["Denver","Colorado Springs","Aurora","Fort Collins","Lakewood","Thornton","Arvada","Westminster","Pueblo","Centennial","Boulder","Highlands Ranch","Greeley","Longmont","Loveland","Broomfield","Castle Rock","Commerce City","Parker","Northglenn","Brighton","Aspen","Vail","Breckenridge","Telluride","Steamboat Springs","Glenwood Springs","Durango","Grand Junction","Estes Park","Keystone","Snowmass","Copper Mountain","Crested Butte","Silverthorne","Dillon"],
    "CT": ["Bridgeport","New Haven","Stamford","Hartford","Waterbury","Norwalk","Danbury","New Britain","Greenwich","Meriden","West Hartford","Bristol","Milford","New London","Hamden","Manchester","Mystic","Torrington","Shelton","Westport"],
    "DE": ["Wilmington","Dover","Newark","Middletown","Smyrna","Milford","Seaford","Georgetown","Elsmere","Rehoboth Beach","Lewes","Bethany Beach","Dewey Beach","Fenwick Island"],
    "FL": ["Jacksonville","Miami","Tampa","Orlando","St Petersburg","Hialeah","Tallahassee","Fort Lauderdale","Port St Lucie","Cape Coral","Pembroke Pines","Hollywood","Miramar","Gainesville","Coral Springs","Clearwater","Miami Gardens","Palm Bay","Pompano Beach","West Palm Beach","Lakeland","Davie","Miami Beach","Sunrise","Plantation","Boca Raton","Deltona","Largo","Deerfield Beach","Melbourne","Palm Beach Gardens","Boynton Beach","Fort Myers","Kissimmee","Weston","Daytona Beach","Homestead","Delray Beach","Tamarac","Pensacola","Sarasota","Naples","Key West","Destin","Panama City Beach","Fort Walton Beach","Ocala","Vero Beach","Marco Island","Amelia Island","St Augustine","Dunedin","Bradenton","Punta Gorda","Port Charlotte","Sebring"],
    "GA": ["Atlanta","Augusta","Columbus","Macon","Savannah","Athens","Sandy Springs","South Fulton","Roswell","Johns Creek","Albany","Warner Robins","Alpharetta","Marietta","Smyrna","Valdosta","Brookhaven","Peachtree City","Dunwoody","Gainesville","Dalton","Kennesaw","Milton","Rome","East Point","Stonecrest","Tybee Island","Jekyll Island","St Simons Island","Helen","Blue Ridge","Dahlonega","Brunswick"],
    "HI": ["Honolulu","East Honolulu","Pearl City","Hilo","Kailua","Waipahu","Kaneohe","Mililani Town","Ewa Beach","Kahului","Kihei","Wailuku","Lahaina","Wailea","Waikiki","Kaanapali","Kailua-Kona","Princeville","Poipu","Kapaa","Lihue","Waimea","Lanai City","Kaunakakai"],
    "ID": ["Boise","Nampa","Meridian","Idaho Falls","Pocatello","Caldwell","Twin Falls","Coeur d'Alene","Lewiston","Post Falls","Rexburg","Moscow","Eagle","Kuna","Ammon","Chubbuck","Sun Valley","Sandpoint","McCall","Hailey"],
    "IL": ["Chicago","Aurora","Joliet","Rockford","Springfield","Elgin","Peoria","Champaign","Waukegan","Naperville","Cicero","Bloomington","Arlington Heights","Evanston","Decatur","Schaumburg","Bolingbrook","Palatine","Skokie","Des Plaines","Orland Park","Tinley Park","Oak Lawn","Berwyn","Mount Prospect","Normal","Wheaton","Downers Grove","Hoffman Estates","Galena"],
    "IN": ["Indianapolis","Fort Wayne","Evansville","South Bend","Carmel","Fishers","Bloomington","Hammond","Gary","Lafayette","Muncie","Terre Haute","Kokomo","Anderson","Noblesville","Greenwood","Elkhart","Mishawaka","Lawrence","Jeffersonville","Columbus","Portage","New Albany","Richmond","Westfield","Valparaiso","French Lick"],
    "IA": ["Des Moines","Cedar Rapids","Davenport","Sioux City","Iowa City","Waterloo","Council Bluffs","Ames","Dubuque","West Des Moines","Ankeny","Urbandale","Cedar Falls","Marion","Bettendorf","Mason City","Clinton","Burlington","Ottumwa","Fort Dodge"],
    "KS": ["Wichita","Overland Park","Kansas City","Olathe","Topeka","Lawrence","Shawnee","Manhattan","Lenexa","Salina","Hutchinson","Leavenworth","Leawood","Dodge City","Garden City","Emporia","Junction City","Liberal","Hays"],
    "KY": ["Louisville","Lexington","Bowling Green","Owensboro","Covington","Richmond","Georgetown","Florence","Hopkinsville","Nicholasville","Elizabethtown","Henderson","Frankfort","Jeffersontown","Paducah","Radcliff","Ashland","Murray","Bardstown","Corbin","Berea"],
    "LA": ["New Orleans","Baton Rouge","Shreveport","Metairie","Lafayette","Lake Charles","Kenner","Bossier City","Monroe","Alexandria","New Iberia","Prairieville","Houma","Central","Laplace","Slidell","Marrero","Mandeville","Covington","Hammond"],
    "ME": ["Portland","Lewiston","Bangor","South Portland","Auburn","Biddeford","Sanford","Augusta","Saco","Westbrook","Bar Harbor","Kennebunkport","Ogunquit","Old Orchard Beach","Camden","Rockland","Boothbay Harbor","Freeport","Acadia","Bethel","Rangeley","Sugarloaf"],
    "MD": ["Baltimore","Frederick","Rockville","Gaithersburg","Bowie","Hagerstown","Annapolis","College Park","Salisbury","Laurel","Greenbelt","Cumberland","Westminster","Hyattsville","Takoma Park","Ocean City","Cambridge","Easton","St Michaels","Bethesda","Silver Spring","Towson"],
    "MA": ["Boston","Worcester","Springfield","Lowell","Cambridge","New Bedford","Brockton","Quincy","Lynn","Fall River","Newton","Somerville","Lawrence","Framingham","Haverhill","Malden","Waltham","Medford","Taunton","Revere","Salem","Plymouth","Cape Cod","Martha's Vineyard","Nantucket","Provincetown","Gloucester","Newburyport","Lenox","Stockbridge","Sturbridge","Northampton"],
    "MI": ["Detroit","Grand Rapids","Warren","Sterling Heights","Lansing","Ann Arbor","Flint","Dearborn","Livonia","Westland","Troy","Farmington Hills","Kalamazoo","Wyoming","Southfield","Rochester Hills","Taylor","St Clair Shores","Pontiac","Dearborn Heights","Royal Oak","Novi","Saginaw","Traverse City","Marquette","Petoskey","Mackinac Island","Holland","Saugatuck","Bay City","Charlevoix","Frankenmuth","Mount Pleasant","Midland","Battle Creek"],
    "MN": ["Minneapolis","St Paul","Rochester","Duluth","Bloomington","Brooklyn Park","Plymouth","St Cloud","Eagan","Woodbury","Coon Rapids","Eden Prairie","Burnsville","Blaine","Lakeville","Minnetonka","Apple Valley","Edina","St Louis Park","Mankato","Moorhead","Shakopee","Stillwater","Brainerd","Bemidji","Walker","Grand Marais","Nisswa","Alexandria","Detroit Lakes","Ely"],
    "MS": ["Jackson","Gulfport","Southaven","Hattiesburg","Biloxi","Meridian","Tupelo","Olive Branch","Greenville","Horn Lake","Pearl","Madison","Ridgeland","Clinton","Starkville","Columbus","Vicksburg","Natchez","Oxford","Ocean Springs","Pascagoula"],
    "MO": ["Kansas City","St Louis","Springfield","Independence","Columbia","Lee's Summit","O'Fallon","St Joseph","St Charles","Blue Springs","Joplin","Chesterfield","Jefferson City","Cape Girardeau","Florissant","St Peters","Branson","Hannibal","Kirksville","Poplar Bluff"],
    "MT": ["Billings","Missoula","Great Falls","Bozeman","Butte","Helena","Kalispell","Havre","Anaconda","Miles City","Belgrade","Livingston","Whitefish","Glacier Park","Polson","Sidney","Glendive","Cut Bank","Lewistown","Hamilton"],
    "NE": ["Omaha","Lincoln","Bellevue","Grand Island","Kearney","Fremont","Hastings","Norfolk","North Platte","Columbus","Papillion","La Vista","Scottsbluff","South Sioux City","Beatrice"],
    "NV": ["Las Vegas","Henderson","Reno","North Las Vegas","Sparks","Carson City","Fernley","Elko","Mesquite","Boulder City","Fallon","Laughlin","Lake Tahoe","Summerlin","Winnemucca"],
    "NH": ["Manchester","Nashua","Concord","Derry","Dover","Rochester","Salem","Merrimack","Londonderry","Hudson","Keene","Portsmouth","Conway","Laconia","North Conway","Hampton Beach","Hanover","Bretton Woods","Littleton","Gorham","Lincoln"],
    "NJ": ["Newark","Jersey City","Paterson","Elizabeth","Edison","Woodbridge","Lakewood","Toms River","Hamilton","Trenton","Clifton","Camden","Brick","Cherry Hill","Passaic","Middletown","Union City","Old Bridge","Bayonne","East Orange","Atlantic City","Cape May","Hoboken","Asbury Park","Ocean City","Wildwood","Long Branch","Seaside Heights","Red Bank","Morristown","Princeton"],
    "NM": ["Albuquerque","Las Cruces","Rio Rancho","Santa Fe","Roswell","Farmington","South Valley","Clovis","Hobbs","Alamogordo","Carlsbad","Gallup","Taos","Ruidoso","Silver City","Truth or Consequences","Cloudcroft","Red River"],
    "NY": ["New York City","Buffalo","Yonkers","Rochester","Syracuse","Albany","New Rochelle","Mount Vernon","Schenectady","Utica","White Plains","Hempstead","Troy","Niagara Falls","Binghamton","Freeport","Valley Stream","Long Beach","Saratoga Springs","Lake Placid","Hamptons","Catskills","Cooperstown","Ithaca","Hudson","Kingston","Poughkeepsie","Newburgh","Olean","Plattsburgh","Watertown","Glens Falls","Oneonta","Corning"],
    "NC": ["Charlotte","Raleigh","Greensboro","Durham","Winston-Salem","Fayetteville","Cary","Wilmington","High Point","Concord","Asheville","Greenville","Gastonia","Jacksonville","Chapel Hill","Rocky Mount","Huntersville","Burlington","Wilson","Kannapolis","Apex","Outer Banks","Boone","Blowing Rock","Pinehurst","New Bern","Beaufort","Morehead City","Kill Devil Hills","Nags Head"],
    "ND": ["Fargo","Bismarck","Grand Forks","Minot","West Fargo","Williston","Dickinson","Mandan","Jamestown","Wahpeton","Devils Lake","Watford City"],
    "OH": ["Columbus","Cleveland","Cincinnati","Toledo","Akron","Dayton","Parma","Canton","Youngstown","Lorain","Hamilton","Springfield","Kettering","Elyria","Lakewood","Cuyahoga Falls","Middletown","Euclid","Newark","Mansfield","Mentor","Cleveland Heights","Beavercreek","Strongsville","Fairfield","Sandusky","Athens","Marietta","Wooster","Zanesville","Findlay","Lima","Chillicothe","Steubenville"],
    "OK": ["Oklahoma City","Tulsa","Norman","Broken Arrow","Lawton","Edmond","Moore","Midwest City","Enid","Stillwater","Muskogee","Bartlesville","Owasso","Shawnee","Ponca City","Ardmore","Tahlequah","Durant","McAlester"],
    "OR": ["Portland","Eugene","Salem","Gresham","Hillsboro","Beaverton","Bend","Medford","Springfield","Corvallis","Albany","Tigard","Lake Oswego","Ashland","Astoria","Cannon Beach","Newport","Lincoln City","Hood River","Seaside","Florence","Coos Bay","Grants Pass","Roseburg","Klamath Falls","Ontario","Baker City"],
    "PA": ["Philadelphia","Pittsburgh","Allentown","Erie","Reading","Scranton","Bethlehem","Lancaster","Harrisburg","York","Altoona","Wilkes-Barre","Chester","Williamsport","Easton","Lebanon","Hazleton","New Castle","McKeesport","Hershey","Gettysburg","Pocono Mountains","State College","Stroudsburg","Jim Thorpe","Doylestown","West Chester","Media","Newtown","New Hope"],
    "RI": ["Providence","Cranston","Warwick","Pawtucket","East Providence","Woonsocket","Coventry","North Providence","Cumberland","West Warwick","Newport","Bristol","Narragansett","Westerly","Block Island","Middletown"],
    "SC": ["Columbia","Charleston","North Charleston","Mount Pleasant","Rock Hill","Greenville","Summerville","Goose Creek","Sumter","Florence","Spartanburg","Myrtle Beach","Hilton Head Island","Conway","Aiken","Greer","Beaufort","Kiawah Island","Isle of Palms","Folly Beach","Pawleys Island","Bluffton"],
    "SD": ["Sioux Falls","Rapid City","Aberdeen","Brookings","Watertown","Mitchell","Yankton","Pierre","Huron","Deadwood","Spearfish","Custer","Hot Springs","Lead","Hill City"],
    "TN": ["Memphis","Nashville","Knoxville","Chattanooga","Clarksville","Murfreesboro","Franklin","Jackson","Johnson City","Bartlett","Hendersonville","Kingsport","Collierville","Cleveland","Smyrna","Germantown","Brentwood","Columbia","Spring Hill","Gatlinburg","Pigeon Forge","Sevierville","Oak Ridge","Cookeville","Tullahoma"],
    "TX": ["Houston","San Antonio","Dallas","Austin","Fort Worth","El Paso","Arlington","Corpus Christi","Plano","Laredo","Lubbock","Garland","Irving","Amarillo","Grand Prairie","Brownsville","Pasadena","Killeen","McKinney","Frisco","Mesquite","McAllen","Midland","Denton","Waco","Carrollton","Pearland","Odessa","Abilene","Beaumont","Round Rock","Richardson","Tyler","Lewisville","Wichita Falls","Sugar Land","College Station","Allen","Edinburg","San Marcos","Galveston","Fredericksburg","South Padre Island","New Braunfels","Kerrville","Boerne","Marble Falls","Georgetown","Bastrop","Dripping Springs"],
    "UT": ["Salt Lake City","West Valley City","Provo","West Jordan","Orem","Sandy","Ogden","St George","Layton","South Jordan","Lehi","Millcreek","Taylorsville","Logan","Murray","Draper","Bountiful","Riverton","Roy","Spanish Fork","Park City","Moab","Zion","Bryce Canyon","Cedar City","Sundance","Midway","Heber City","Kanab","Springdale"],
    "VT": ["Burlington","Essex","South Burlington","Colchester","Rutland","Bennington","Brattleboro","Hartford","Milton","Springfield","Stowe","Montpelier","Middlebury","Woodstock","Manchester","Killington","Warren","Shelburne","Barre","Newport","St Johnsbury","Morrisville"],
    "VA": ["Virginia Beach","Norfolk","Chesapeake","Arlington","Richmond","Newport News","Alexandria","Hampton","Roanoke","Portsmouth","Suffolk","Lynchburg","Harrisonburg","Charlottesville","Blacksburg","Danville","Manassas","Petersburg","Fredericksburg","Williamsburg","Leesburg","Winchester","Staunton","Waynesboro","Bristol","Luray","Hot Springs","Chincoteague","Assateague","Lexington"],
    "WA": ["Seattle","Spokane","Tacoma","Vancouver","Bellevue","Kent","Everett","Renton","Spokane Valley","Federal Way","Kirkland","Bellingham","Kennewick","Yakima","Redmond","Marysville","Pasco","Sammamish","Lakewood","Shoreline","Richland","Burien","Olympia","Auburn","Bothell","Edmonds","Puyallup","Wenatchee","Leavenworth","Winthrop","Port Townsend","Anacortes","Port Angeles","Mount Vernon","Bremerton"],
    "WV": ["Charleston","Huntington","Morgantown","Parkersburg","Wheeling","Weirton","Fairmont","Martinsburg","Beckley","Clarksburg","South Charleston","St Albans","Lewisburg","Harpers Ferry","Snowshoe","White Sulphur Springs"],
    "WI": ["Milwaukee","Madison","Green Bay","Kenosha","Racine","Appleton","Waukesha","Oshkosh","Eau Claire","Janesville","West Allis","La Crosse","Sheboygan","Wauwatosa","Fond du Lac","New Berlin","Wausau","Brookfield","Beloit","Greenfield","Wisconsin Dells","Door County","Lake Geneva","Bayfield","Rhinelander","Minocqua","Wisconsin Rapids","Marshfield","Manitowoc","Two Rivers"],
    "WY": ["Cheyenne","Casper","Laramie","Gillette","Rock Springs","Sheridan","Green River","Evanston","Riverton","Jackson","Cody","Dubois","Thermopolis","Lander","Pinedale"],
    # ── Canada ─────────────────────────────────────────────────────────────────
    "BC": ["Vancouver","Surrey","Burnaby","Richmond","Kelowna","Abbotsford","Coquitlam","Langley","Saanich","Delta","Kamloops","Nanaimo","Chilliwack","Prince George","Victoria","Whistler","Penticton","Vernon","Tofino","Ucluelet","Sun Peaks","Revelstoke","Nelson","Cranbrook","Fernie","Kimberley","Salmon Arm","Trail","Courtenay","Campbell River","Powell River"],
    "AB": ["Calgary","Edmonton","Red Deer","Lethbridge","St Albert","Medicine Hat","Grande Prairie","Airdrie","Spruce Grove","Leduc","Okotoks","Fort McMurray","Camrose","Banff","Canmore","Jasper","Lake Louise","Drumheller","Pincher Creek","Lacombe","Wetaskiwin","Innisfail"],
    "ON": ["Toronto","Ottawa","Mississauga","Brampton","Hamilton","London","Markham","Vaughan","Kitchener","Windsor","Burlington","Oakville","Sudbury","Oshawa","Barrie","Whitby","Richmond Hill","Cambridge","Kingston","Ajax","Thunder Bay","Niagara Falls","Waterloo","Guelph","Brantford","Muskoka","Collingwood","Prince Edward County","Huntsville","Parry Sound","Midland","Gravenhurst","Bracebridge","Owen Sound","Tobermory","Stratford","St Catharines","Peterborough"],
    "QC": ["Montreal","Quebec City","Laval","Gatineau","Longueuil","Sherbrooke","Saguenay","Trois-Rivieres","Terrebonne","Saint-Jean-sur-Richelieu","Repentigny","Brossard","Drummondville","Saint-Jerome","Granby","Mont-Tremblant","Charlevoix","Magog","Bromont","Sutton","Saint-Sauveur","Orford","Rimouski","Rouyn-Noranda","Val-d'Or"],
    "NS": ["Halifax","Cape Breton","Truro","New Glasgow","Glace Bay","Dartmouth","Bridgewater","Amherst","Antigonish","Wolfville","Kentville","Windsor","Digby","Yarmouth","Lunenburg","Shelburne","Liverpool","Annapolis Royal"],
    "NB": ["Moncton","Saint John","Fredericton","Dieppe","Riverview","Miramichi","Campbellton","Bathurst","Edmundston","Sackville","St Andrews","Sussex","Woodstock"],
    "MB": ["Winnipeg","Brandon","Steinbach","Winkler","Thompson","Portage la Prairie","Selkirk","Morden","Dauphin","The Pas","Churchill","Flin Flon"],
    "SK": ["Saskatoon","Regina","Prince Albert","Moose Jaw","Swift Current","Yorkton","North Battleford","Estevan","Weyburn","Lloydminster","Melfort","Humboldt"],
    "PE": ["Charlottetown","Summerside","Stratford","Cornwall","Cavendish","Brackley Beach","Souris","Montague","Kensington"],
    "NL": ["St John's","Conception Bay South","Mount Pearl","Corner Brook","Paradise","Grand Falls-Windsor","Gander","Happy Valley-Goose Bay","Labrador City","Stephenville","Marystown","Twillingate","Trinity","Bonavista","Ferryland","Clarenville"],
    # ── Australia ──────────────────────────────────────────────────────────────
    "NSW": ["Sydney","Newcastle","Wollongong","Coffs Harbour","Albury","Wagga Wagga","Port Macquarie","Tamworth","Orange","Dubbo","Broken Hill","Lismore","Bathurst","Armidale","Queanbeyan","Nowra","Bega","Goulburn","Griffith","Maitland","Cessnock","Byron Bay","Hunter Valley","Blue Mountains","Jervis Bay","Shoalhaven","Tweed Heads","Ballina","Murwillumbah","Yamba"],
    "VIC": ["Melbourne","Geelong","Ballarat","Bendigo","Shepparton","Mildura","Warrnambool","Traralgon","Wodonga","Horsham","Sale","Ararat","Hamilton","Benalla","Wangaratta","Bairnsdale","Echuca","Mornington","Frankston","Dandenong","Ringwood","Box Hill","Williamstown","St Kilda","Phillip Island","Apollo Bay","Lorne","Torquay","Mount Buller","Falls Creek","Bright","Healesville","Yarra Valley","Daylesford","Hepburn Springs","Queenscliff"],
    "QLD": ["Brisbane","Gold Coast","Sunshine Coast","Townsville","Cairns","Toowoomba","Rockhampton","Mackay","Bundaberg","Hervey Bay","Gladstone","Maryborough","Nambour","Caloundra","Maroochydore","Noosa","Innisfail","Mount Isa","Emerald","Charleville","Longreach","Roma","Port Douglas","Mission Beach","Airlie Beach","Hamilton Island","Whitsundays","Magnetic Island","Mossman","Palm Cove","Trinity Beach"],
    "WA":  ["Perth","Fremantle","Rockingham","Mandurah","Bunbury","Geraldton","Kalgoorlie","Albany","Broome","Port Hedland","Karratha","Esperance","Busselton","Margaret River","Exmouth","Carnarvon","Tom Price","Newman","Rottnest Island","Northam","Collie","Harvey","Manjimup","Denmark"],
    "SA":  ["Adelaide","Mount Gambier","Whyalla","Murray Bridge","Port Augusta","Port Pirie","Victor Harbor","Gawler","Port Lincoln","Millicent","Kangaroo Island","Barossa Valley","McLaren Vale","Clare Valley","Willunga","Strathalbyn","Hahndorf","Tanunda","Nuriootpa","Robe","Beachport","Naracoorte"],
    "TAS": ["Hobart","Launceston","Devonport","Burnie","Ulverstone","Queenstown","Strahan","Cradle Mountain","Freycinet","Bicheno","St Helens","St Marys","Swansea","Orford","Port Arthur","Richmond","Ross","Campbell Town","Longford","Evandale","Deloraine","Penguin","Stanley","Smithton","Wynyard"],
    "NT":  ["Darwin","Alice Springs","Palmerston","Katherine","Tennant Creek","Nhulunbuy","Kakadu","Uluru","Litchfield","Nitmiluk","Jabiru","Yulara"],
    "ACT": ["Canberra","Belconnen","Tuggeranong","Woden","Gungahlin","Queanbeyan"],
}


class ScrapeRequest(BaseModel):
    category_label: str
    states: list[str] = []
    selected_cities: list[str] = []    # if non-empty, only search these cities within the selected states
    custom_locations: list[str] = []   # e.g. ["Miami Beach, FL", "Aspen, CO"]
    hunter_credits: int = 0   # max Hunter.io credits to spend on this job (0 = none / default OFF)
    max_results_per_city: int = 20


@router.get("/categories")
def get_categories():
    return GOOGLE_CATEGORIES


@router.get("/cities")
def get_cities():
    """Returns all known cities grouped by state code."""
    return STATE_CITIES


@router.get("/status")
def get_status():
    """Shows which API keys are configured."""
    return {
        "google_places": bool(os.getenv("GOOGLE_PLACES_API_KEY")),
        "hunter":        bool(os.getenv("HUNTER_API_KEY")),
        "email_fallback": True,   # web scraper is always available
    }


@router.post("/run")
async def run_scrape(
    payload: ScrapeRequest,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    cat = next((c for c in GOOGLE_CATEGORIES if c["label"] == payload.category_label), None)
    if not cat:
        return {"error": f"Unknown category: {payload.category_label}"}

    # Build city-level location list
    locations: list[str] = []
    for state in payload.states:
        all_cities = STATE_CITIES.get(state, [])
        if payload.selected_cities:
            # Only use cities the user explicitly chose that belong to this state
            cities = [c for c in all_cities if c in payload.selected_cities]
            if not cities:
                continue  # user selected cities but none match this state — skip
        else:
            cities = all_cities  # Any city — use all known cities for this state

        if cities:
            locations.extend([f"{city}, {state}" for city in cities])
        else:
            locations.append(state)  # state has no known cities, search state-level

    # Add custom locations directly
    for loc in payload.custom_locations:
        if loc.strip() and loc.strip() not in locations:
            locations.append(loc.strip())

    job = ScrapeJob(
        category=payload.category_label,
        location=", ".join(payload.states),
        status="pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background.add_task(_scrape_task, job.id, cat["query"], locations, payload.hunter_credits, payload.max_results_per_city)
    return {"job_id": job.id, "status": "started", "locations_queued": len(locations)}


@router.get("/jobs")
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(ScrapeJob).order_by(ScrapeJob.created_at.desc()).limit(50).all()
    return [_serialize_job(j) for j in jobs]


@router.get("/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
    if not job:
        return {"error": "Job not found"}
    return _serialize_job(job)


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
    if not job:
        return {"error": "Job not found"}
    if job.status == "running":
        _cancel_requested.add(job_id)
    # Also mark any non-running stuck jobs directly
    if job.status in ("running", "pending"):
        job.status = "stopped"
        job.finished_at = datetime.utcnow()
        db.commit()
    return {"job_id": job_id, "status": "stopped"}


# ── Background task ──────────────────────────────────────────────────────────

LEAD_COLUMNS = {c.name for c in Lead.__table__.columns}


async def _scrape_task(job_id: int, query: str, locations: list[str], hunter_credits: int = 5, payload_max_results: int = 20):
    db = SessionLocal()
    try:
        job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
        if not job:
            return
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()

        total_saved = 0
        # Mutable counter shared across all location searches in this job
        hunter_used = [0]

        for location in locations:
            # Check if user cancelled this job
            if job_id in _cancel_requested:
                _cancel_requested.discard(job_id)
                job.status = "stopped"
                job.leads_found = total_saved
                job.finished_at = datetime.utcnow()
                db.commit()
                return

            try:
                results = await search_businesses(
                    query, location,
                    max_results=payload_max_results,
                    hunter_budget=hunter_credits,
                    hunter_used=hunter_used,
                )
            except Exception:
                continue

            for biz in results:
                # Deduplicate by name + city
                exists = db.query(Lead).filter(
                    Lead.business_name == biz.get("business_name"),
                    Lead.city == biz.get("city"),
                ).first()
                if exists:
                    continue
                lead = Lead(**{k: v for k, v in biz.items() if k in LEAD_COLUMNS})
                db.add(lead)
                total_saved += 1

            db.commit()
            await asyncio.sleep(2)  # respect API rate limits

        job.status = "done"
        job.leads_found = total_saved
        job.finished_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
        if job:
            job.status = "failed"
            job.error = str(e)
            job.finished_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


def _serialize_job(job: ScrapeJob) -> dict:
    return {
        "id":          job.id,
        "category":    job.category,
        "location":    job.location,
        "status":      job.status,
        "leads_found": job.leads_found,
        "error":       job.error,
        "started_at":  job.started_at.isoformat()  if job.started_at  else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "created_at":  job.created_at.isoformat()  if job.created_at  else None,
    }
