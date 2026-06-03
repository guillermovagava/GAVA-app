import { useState, useEffect, useRef } from 'react'
import { getScrapeJobs, cancelJob } from '../../api/client'
import axios from 'axios'

const COUNTRIES = [
  { code: 'US', label: '🇺🇸 United States' },
  { code: 'CA', label: '🇨🇦 Canada' },
  { code: 'AU', label: '🇦🇺 Australia' },
]

const STATES_BY_COUNTRY = {
  US: ['AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN',
       'IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV',
       'NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN',
       'TX','UT','VT','VA','WA','WV','WI','WY'],
  CA: ['BC','AB','ON','QC','NS','NB','MB','SK','PE','NL'],
  AU: ['NSW','VIC','QLD','WA','SA','TAS','NT','ACT'],
}

// Mirror of backend STATE_CITIES — all significant cities per state
const CITIES_BY_STATE = {
  // ── United States ──────────────────────────────────────────────────────────
  AL: ['Birmingham','Montgomery','Huntsville','Mobile','Tuscaloosa','Hoover','Auburn','Dothan','Decatur','Madison','Gadsden','Florence','Anniston','Gulf Shores','Orange Beach','Prattville','Vestavia Hills','Phenix City'],
  AK: ['Anchorage','Fairbanks','Juneau','Sitka','Ketchikan','Wasilla','Kenai','Kodiak','Bethel','Palmer','Skagway','Homer','Valdez','Seward','Soldotna'],
  AZ: ['Phoenix','Tucson','Mesa','Chandler','Scottsdale','Glendale','Gilbert','Tempe','Peoria','Surprise','Yuma','Flagstaff','Goodyear','Avondale','Sedona','Prescott','Lake Havasu City','Kingman','Bullhead City','Show Low','Sierra Vista','Casa Grande','Maricopa'],
  AR: ['Little Rock','Fayetteville','Fort Smith','Springdale','Jonesboro','Conway','Rogers','North Little Rock','Pine Bluff','Bentonville','Hot Springs','Texarkana','Sherwood','Jacksonville','Russellville','Bella Vista','West Memphis','Eureka Springs'],
  CA: ['Los Angeles','San Diego','San Jose','San Francisco','Fresno','Sacramento','Long Beach','Oakland','Bakersfield','Anaheim','Santa Ana','Riverside','Stockton','Irvine','Chula Vista','Fremont','San Bernardino','Modesto','Fontana','Moreno Valley','Glendale','Oxnard','Huntington Beach','Santa Clarita','Garden Grove','Santa Rosa','Oceanside','Rancho Cucamonga','Ontario','Lancaster','Elk Grove','Palmdale','Corona','Salinas','Pomona','Torrance','Sunnyvale','Escondido','Pasadena','Fullerton','Hayward','Miramar','Temecula','Visalia','Simi Valley','Concord','Roseville','Santa Clara','Victorville','Thousand Oaks','El Monte','Murrieta','Vallejo','Berkeley','Carlsbad','Downey','Costa Mesa','Inglewood','San Buenaventura','Ventura','West Covina','Norwalk','Antioch','Santa Barbara','Chico','El Cajon','Rialto','Richmond','Murrieta','Burbank','Daly City','Santa Maria','Westminster','Clovis','Jurupa Valley','El Monte','Napa','Palm Springs','Carmel','Monterey','Santa Cruz','Laguna Beach','Newport Beach','Malibu','Beverly Hills','Santa Monica','Big Sur','Sonoma','Lake Tahoe','South Lake Tahoe'],
  CO: ['Denver','Colorado Springs','Aurora','Fort Collins','Lakewood','Thornton','Arvada','Westminster','Pueblo','Centennial','Boulder','Highlands Ranch','Greeley','Longmont','Loveland','Broomfield','Castle Rock','Commerce City','Parker','Northglenn','Brighton','Aspen','Vail','Breckenridge','Telluride','Steamboat Springs','Glenwood Springs','Durango','Grand Junction','Estes Park','Keystone','Snowmass','Copper Mountain','Crested Butte','Silverthorne','Dillon'],
  CT: ['Bridgeport','New Haven','Stamford','Hartford','Waterbury','Norwalk','Danbury','New Britain','Greenwich','Meriden','West Hartford','Bristol','Milford','New London','Hamden','Manchester','Mystic','Torrington','Shelton','Westport'],
  DE: ['Wilmington','Dover','Newark','Middletown','Smyrna','Milford','Seaford','Georgetown','Elsmere','Rehoboth Beach','Lewes','Bethany Beach','Dewey Beach','Fenwick Island'],
  FL: ['Jacksonville','Miami','Tampa','Orlando','St Petersburg','Hialeah','Tallahassee','Fort Lauderdale','Port St Lucie','Cape Coral','Pembroke Pines','Hollywood','Miramar','Gainesville','Coral Springs','Clearwater','Miami Gardens','Palm Bay','Pompano Beach','West Palm Beach','Lakeland','Davie','Miami Beach','Sunrise','Plantation','Boca Raton','Deltona','Largo','Deerfield Beach','Melbourne','Palm Beach Gardens','Boynton Beach','Fort Myers','Kissimmee','Weston','Daytona Beach','Homestead','Delray Beach','Tamarac','Pensacola','Sarasota','Naples','Key West','Destin','Panama City Beach','Fort Walton Beach','Ocala','Gainesville','Vero Beach','Marco Island','Amelia Island','St Augustine','Dunedin','Bradenton','Punta Gorda','Port Charlotte','Sebring'],
  GA: ['Atlanta','Augusta','Columbus','Macon','Savannah','Athens','Sandy Springs','South Fulton','Roswell','Johns Creek','Albany','Warner Robins','Alpharetta','Marietta','Smyrna','Valdosta','Brookhaven','Peachtree City','Dunwoody','Gainesville','Dalton','Kennesaw','Milton','Rome','East Point','Stonecrest','Tybee Island','Jekyll Island','St Simons Island','Helen','Blue Ridge','Dahlonega','Brunswick'],
  HI: ['Honolulu','East Honolulu','Pearl City','Hilo','Kailua','Waipahu','Kaneohe','Mililani Town','Ewa Beach','Kahului','Kihei','Wailuku','Lahaina','Wailea','Waikiki','Kaanapali','Kailua-Kona','Princeville','Poipu','Kapaa','Lihue','Waimea','Lanai City','Kaunakakai'],
  ID: ['Boise','Nampa','Meridian','Idaho Falls','Pocatello','Caldwell','Twin Falls','Coeur d\'Alene','Lewiston','Post Falls','Rexburg','Moscow','Eagle','Kuna','Ammon','Chubbuck','Sun Valley','Sandpoint','McCall','Hailey'],
  IL: ['Chicago','Aurora','Joliet','Rockford','Springfield','Elgin','Peoria','Champaign','Waukegan','Naperville','Cicero','Bloomington','Arlington Heights','Evanston','Decatur','Schaumburg','Bolingbrook','Palatine','Skokie','Des Plaines','Orland Park','Tinley Park','Oak Lawn','Berwyn','Mount Prospect','Normal','Wheaton','Downers Grove','Hoffman Estates','Galena'],
  IN: ['Indianapolis','Fort Wayne','Evansville','South Bend','Carmel','Fishers','Bloomington','Hammond','Gary','Lafayette','Muncie','Terre Haute','Kokomo','Anderson','Noblesville','Greenwood','Elkhart','Mishawaka','Lawrence','Jeffersonville','Columbus','Portage','New Albany','Richmond','Westfield','Valparaiso','French Lick'],
  IA: ['Des Moines','Cedar Rapids','Davenport','Sioux City','Iowa City','Waterloo','Council Bluffs','Ames','Dubuque','West Des Moines','Ankeny','Urbandale','Cedar Falls','Marion','Bettendorf','Mason City','Clinton','Burlington','Ottumwa','Fort Dodge'],
  KS: ['Wichita','Overland Park','Kansas City','Olathe','Topeka','Lawrence','Shawnee','Manhattan','Lenexa','Salina','Hutchinson','Leavenworth','Leawood','Dodge City','Garden City','Emporia','Junction City','Liberal','Hays'],
  KY: ['Louisville','Lexington','Bowling Green','Owensboro','Covington','Richmond','Georgetown','Florence','Hopkinsville','Nicholasville','Elizabethtown','Henderson','Frankfort','Jeffersontown','Paducah','Radcliff','Ashland','Murray','Bardstown','Corbin','Gatlinburg area','Berea'],
  LA: ['New Orleans','Baton Rouge','Shreveport','Metairie','Lafayette','Lake Charles','Kenner','Bossier City','Monroe','Alexandria','New Iberia','Prairieville','Houma','Central','Laplace','Slidell','Marrero','Mandeville','Covington','Hammond'],
  ME: ['Portland','Lewiston','Bangor','South Portland','Auburn','Biddeford','Sanford','Augusta','Saco','Westbrook','Bar Harbor','Kennebunkport','Ogunquit','Old Orchard Beach','Camden','Rockland','Boothbay Harbor','Freeport','Acadia','Bethel','Rangeley','Sugarloaf'],
  MD: ['Baltimore','Frederick','Rockville','Gaithersburg','Bowie','Hagerstown','Annapolis','College Park','Salisbury','Laurel','Greenbelt','Cumberland','Westminster','Hyattsville','Takoma Park','Ocean City','Cambridge','Easton','St Michaels','Bethesda','Chevy Chase','Silver Spring','Towson'],
  MA: ['Boston','Worcester','Springfield','Lowell','Cambridge','New Bedford','Brockton','Quincy','Lynn','Fall River','Newton','Somerville','Lawrence','Framingham','Haverhill','Malden','Waltham','Medford','Taunton','Revere','Salem','Plymouth','Cape Cod','Martha\'s Vineyard','Nantucket','Provincetown','Gloucester','Newburyport','Lenox','Stockbridge','Sturbridge','Northampton'],
  MI: ['Detroit','Grand Rapids','Warren','Sterling Heights','Lansing','Ann Arbor','Flint','Dearborn','Livonia','Westland','Troy','Farmington Hills','Kalamazoo','Wyoming','Southfield','Rochester Hills','Taylor','St Clair Shores','Pontiac','Dearborn Heights','Royal Oak','Novi','Saginaw','Traverse City','Marquette','Petoskey','Mackinac Island','Holland','Saugatuck','Bay City','Charlevoix','Frankenmuth','Mount Pleasant','Midland','Battle Creek'],
  MN: ['Minneapolis','St Paul','Rochester','Duluth','Bloomington','Brooklyn Park','Plymouth','St Cloud','Eagan','Woodbury','Coon Rapids','Eden Prairie','Burnsville','Blaine','Lakeville','Minnetonka','Apple Valley','Edina','St Louis Park','Mankato','Moorhead','Shakopee','Maplewood','Cottage Grove','Richfield','Duluth','Stillwater','Brainerd','Bemidji','Walker','Grand Marais','Nisswa','Alexandria','Detroit Lakes','Ely'],
  MS: ['Jackson','Gulfport','Southaven','Hattiesburg','Biloxi','Meridian','Tupelo','Olive Branch','Greenville','Horn Lake','Pearl','Madison','Ridgeland','Clinton','Starkville','Columbus','Vicksburg','Natchez','Oxford','Ocean Springs','Pascagoula'],
  MO: ['Kansas City','St Louis','Springfield','Independence','Columbia','Lee\'s Summit','O\'Fallon','St Joseph','St Charles','Blue Springs','Joplin','Chesterfield','Jefferson City','Cape Girardeau','Florissant','St Peters','Branson','Hannibal','Kirksville','Poplar Bluff'],
  MT: ['Billings','Missoula','Great Falls','Bozeman','Butte','Helena','Kalispell','Havre','Anaconda','Miles City','Belgrade','Livingston','Whitefish','Glacier Park','Polson','Sidney','Glendive','Cut Bank','Lewistown','Hamilton'],
  NE: ['Omaha','Lincoln','Bellevue','Grand Island','Kearney','Fremont','Hastings','Norfolk','North Platte','Columbus','Papillion','La Vista','Scottsbluff','South Sioux City','Beatrice'],
  NV: ['Las Vegas','Henderson','Reno','North Las Vegas','Sparks','Carson City','Fernley','Elko','Mesquite','Boulder City','Fallon','Laughlin','Lake Tahoe','Summerlin','Winnemucca'],
  NH: ['Manchester','Nashua','Concord','Derry','Dover','Rochester','Salem','Merrimack','Londonderry','Hudson','Keene','Portsmouth','Conway','Laconia','North Conway','Hampton Beach','Hanover','Bretton Woods','Littleton','Gorham','Lincoln'],
  NJ: ['Newark','Jersey City','Paterson','Elizabeth','Edison','Woodbridge','Lakewood','Toms River','Hamilton','Trenton','Clifton','Camden','Brick','Cherry Hill','Passaic','Middletown','Union City','Old Bridge','Bayonne','East Orange','Atlantic City','Cape May','Hoboken','Asbury Park','Ocean City','Wildwood','Long Branch','Seaside Heights','Red Bank','Morristown','Princeton'],
  NM: ['Albuquerque','Las Cruces','Rio Rancho','Santa Fe','Roswell','Farmington','South Valley','Clovis','Hobbs','Alamogordo','Carlsbad','Gallup','Taos','Ruidoso','Silver City','Truth or Consequences','Cloudcroft','Red River'],
  NY: ['New York City','Buffalo','Yonkers','Rochester','Syracuse','Albany','New Rochelle','Mount Vernon','Schenectady','Utica','White Plains','Hempstead','Troy','Niagara Falls','Binghamton','Freeport','Valley Stream','Long Beach','Saratoga Springs','Lake Placid','Hamptons','Catskills','Cooperstown','Ithaca','Hudson','Kingston','Poughkeepsie','Newburgh','Olean','Plattsburgh','Watertown','Glens Falls','Oneonta','Corning'],
  NC: ['Charlotte','Raleigh','Greensboro','Durham','Winston-Salem','Fayetteville','Cary','Wilmington','High Point','Concord','Asheville','Greenville','Gastonia','Jacksonville','Chapel Hill','Rocky Mount','Huntersville','Burlington','Wilson','Kannapolis','Apex','Outer Banks','Boone','Blowing Rock','Pinehurst','New Bern','Beaufort','Morehead City','Kill Devil Hills','Nags Head'],
  ND: ['Fargo','Bismarck','Grand Forks','Minot','West Fargo','Williston','Dickinson','Mandan','Jamestown','Wahpeton','Devils Lake','Watford City'],
  OH: ['Columbus','Cleveland','Cincinnati','Toledo','Akron','Dayton','Parma','Canton','Youngstown','Lorain','Hamilton','Springfield','Kettering','Elyria','Lakewood','Cuyahoga Falls','Middletown','Euclid','Newark','Mansfield','Mentor','Cleveland Heights','Beavercreek','Strongsville','Fairfield','Sandusky','Athens','Marietta','Wooster','Zanesville','Findlay','Lima','Chillicothe','Steubenville'],
  OK: ['Oklahoma City','Tulsa','Norman','Broken Arrow','Lawton','Edmond','Moore','Midwest City','Enid','Stillwater','Muskogee','Bartlesville','Owasso','Shawnee','Ponca City','Ardmore','Tahlequah','Durant','McAlester'],
  OR: ['Portland','Eugene','Salem','Gresham','Hillsboro','Beaverton','Bend','Medford','Springfield','Corvallis','Albany','Tigard','Lake Oswego','Ashland','Astoria','Cannon Beach','Newport','Lincoln City','Hood River','Seaside','Florence','Coos Bay','Grants Pass','Roseburg','Klamath Falls','Ontario','Baker City'],
  PA: ['Philadelphia','Pittsburgh','Allentown','Erie','Reading','Scranton','Bethlehem','Lancaster','Harrisburg','York','Altoona','Wilkes-Barre','Chester','Williamsport','Easton','Lebanon','Hazleton','New Castle','McKeesport','Hershey','Gettysburg','Pocono Mountains','State College','Stroudsburg','Jim Thorpe','Doylestown','West Chester','Media','Newtown','New Hope'],
  RI: ['Providence','Cranston','Warwick','Pawtucket','East Providence','Woonsocket','Coventry','North Providence','Cumberland','West Warwick','Newport','Bristol','Narragansett','Westerly','Block Island','Middletown'],
  SC: ['Columbia','Charleston','North Charleston','Mount Pleasant','Rock Hill','Greenville','Summerville','Goose Creek','Hilton Head','Sumter','Florence','Spartanburg','Myrtle Beach','Hilton Head Island','Conway','Aiken','Greer','Beaufort','Kiawah Island','Isle of Palms','Folly Beach','Pawleys Island','Bluffton'],
  SD: ['Sioux Falls','Rapid City','Aberdeen','Brookings','Watertown','Mitchell','Yankton','Pierre','Huron','Deadwood','Spearfish','Custer','Hot Springs','Lead','Hill City'],
  TN: ['Memphis','Nashville','Knoxville','Chattanooga','Clarksville','Murfreesboro','Franklin','Jackson','Johnson City','Bartlett','Hendersonville','Kingsport','Collierville','Cleveland','Smyrna','Germantown','Brentwood','Columbia','Spring Hill','Gatlinburg','Pigeon Forge','Sevierville','Oak Ridge','Cookeville','Tullahoma'],
  TX: ['Houston','San Antonio','Dallas','Austin','Fort Worth','El Paso','Arlington','Corpus Christi','Plano','Laredo','Lubbock','Garland','Irving','Amarillo','Grand Prairie','Brownsville','Pasadena','Killeen','McKinney','Frisco','Mesquite','McAllen','Midland','Denton','Waco','Carrollton','Pearland','Odessa','Abilene','Beaumont','Round Rock','Richardson','Tyler','Lewisville','Wichita Falls','Sugar Land','College Station','Allen','Edinburg','San Marcos','El Paso','Galveston','Fredericksburg','South Padre Island','New Braunfels','Kerrville','Boerne','Marble Falls','Georgetown','Bastrop','Dripping Springs'],
  UT: ['Salt Lake City','West Valley City','Provo','West Jordan','Orem','Sandy','Ogden','St George','Layton','South Jordan','Lehi','Millcreek','Taylorsville','Logan','Murray','Draper','Bountiful','Riverton','Roy','Spanish Fork','Park City','Moab','Zion','Bryce Canyon','Cedar City','Sundance','Midway','Heber City','Kanab','Springdale'],
  VT: ['Burlington','Essex','South Burlington','Colchester','Rutland','Bennington','Brattleboro','Hartford','Milton','Springfield','Stowe','Montpelier','Middlebury','Woodstock','Manchester','Killington','Warren','Stowe','Shelburne','Barre','Newport','St Johnsbury','Morrisville'],
  VA: ['Virginia Beach','Norfolk','Chesapeake','Arlington','Richmond','Newport News','Alexandria','Hampton','Roanoke','Portsmouth','Suffolk','Lynchburg','Harrisonburg','Charlottesville','Blacksburg','Danville','Manassas','Petersburg','Fredericksburg','Williamsburg','Leesburg','Winchester','Staunton','Waynesboro','Bristol','Luray','Hot Springs','Chincoteague','Assateague','Lexington'],
  WA: ['Seattle','Spokane','Tacoma','Vancouver','Bellevue','Kent','Everett','Renton','Spokane Valley','Federal Way','Kirkland','Bellingham','Kennewick','Yakima','Redmond','Marysville','Pasco','Sammamish','Lakewood','Shoreline','Richland','Burien','Olympia','Auburn','Bothell','Edmonds','Puyallup','Lakewood','Wenatchee','Leavenworth','Winthrop','Port Townsend','Anacortes','Whidbey Island','Port Angeles','Mount Vernon','Bremerton'],
  WV: ['Charleston','Huntington','Morgantown','Parkersburg','Wheeling','Weirton','Fairmont','Martinsburg','Beckley','Clarksburg','South Charleston','St Albans','Lewisburg','Harpers Ferry','Snowshoe','White Sulphur Springs'],
  WI: ['Milwaukee','Madison','Green Bay','Kenosha','Racine','Appleton','Waukesha','Oshkosh','Eau Claire','Janesville','West Allis','La Crosse','Sheboygan','Wauwatosa','Fond du Lac','New Berlin','Wausau','Brookfield','Beloit','Greenfield','Wisconsin Dells','Door County','Lake Geneva','Bayfield','Rhinelander','Minocqua','Wisconsin Rapids','Marshfield','Manitowoc','Two Rivers'],
  WY: ['Cheyenne','Casper','Laramie','Gillette','Rock Springs','Sheridan','Green River','Evanston','Riverton','Jackson','Cody','Dubois','Thermopolis','Lander','Pinedale'],
  // ── Canada ─────────────────────────────────────────────────────────────────
  BC: ['Vancouver','Surrey','Burnaby','Richmond','Kelowna','Abbotsford','Coquitlam','Langley','Saanich','Delta','Kamloops','Nanaimo','Chilliwack','Prince George','Victoria','Whistler','Penticton','Vernon','Tofino','Ucluelet','Sun Peaks','Revelstoke','Nelson','Cranbrook','Fernie','Kimberley','Salmon Arm','Trail','Courtenay','Campbell River','Powell River'],
  AB: ['Calgary','Edmonton','Red Deer','Lethbridge','St Albert','Medicine Hat','Grande Prairie','Airdrie','Spruce Grove','Leduc','Okotoks','Fort McMurray','Camrose','Banff','Canmore','Jasper','Lake Louise','Drumheller','Pincher Creek','Lacombe','Wetaskiwin','Innisfail'],
  ON: ['Toronto','Ottawa','Mississauga','Brampton','Hamilton','London','Markham','Vaughan','Kitchener','Windsor','Burlington','Oakville','Sudbury','Oshawa','Barrie','Whitby','Richmond Hill','Cambridge','Kingston','Ajax','Thunder Bay','Niagara Falls','Waterloo','Guelph','Brantford','Muskoka','Collingwood','Blue Mountain','Prince Edward County','Thousand Islands','Huntsville','Parry Sound','Midland','Gravenhurst','Bracebridge','Owen Sound','Tobermory','Stratford','St Catharines','Peterborough'],
  QC: ['Montreal','Quebec City','Laval','Gatineau','Longueuil','Sherbrooke','Saguenay','Trois-Rivieres','Terrebonne','Saint-Jean-sur-Richelieu','Repentigny','Brossard','Drummondville','Saint-Jerome','Granby','Mont-Tremblant','Charlevoix','Magog','Bromont','Sutton','Saint-Sauveur','Orford','Lac-Mégantic','Rimouski','Rouyn-Noranda','Val-d\'Or'],
  NS: ['Halifax','Cape Breton','Truro','New Glasgow','Glace Bay','Dartmouth','Bridgewater','Amherst','Antigonish','Wolfville','Kentville','Windsor','Digby','Yarmouth','Lunenburg','Shelburne','Liverpool','Annapolis Royal'],
  NB: ['Moncton','Saint John','Fredericton','Dieppe','Riverview','Miramichi','Campbellton','Bathurst','Edmundston','Sackville','St Andrews','Sussex','Woodstock'],
  MB: ['Winnipeg','Brandon','Steinbach','Winkler','Thompson','Portage la Prairie','Selkirk','Morden','Dauphin','The Pas','Churchill','Flin Flon'],
  SK: ['Saskatoon','Regina','Prince Albert','Moose Jaw','Swift Current','Yorkton','North Battleford','Estevan','Weyburn','Lloydminster','Melfort','Humboldt'],
  PE: ['Charlottetown','Summerside','Stratford','Cornwall','Cavendish','Brackley Beach','Souris','Montague','Kensington'],
  NL: ['St John\'s','Conception Bay South','Mount Pearl','Corner Brook','Paradise','Grand Falls-Windsor','Gander','Happy Valley-Goose Bay','Labrador City','Stephenville','Marystown','Twillingate','Trinity','Bonavista','Ferryland','Clarenville'],
  // ── Australia ──────────────────────────────────────────────────────────────
  NSW: ['Sydney','Newcastle','Wollongong','Coffs Harbour','Albury','Wagga Wagga','Port Macquarie','Tamworth','Orange','Dubbo','Broken Hill','Lismore','Bathurst','Armidale','Queanbeyan','Nowra','Bega','Goulburn','Griffith','Maitland','Cessnock','Byron Bay','Hunter Valley','Blue Mountains','Jervis Bay','Shoalhaven','Tweed Heads','Ballina','Murwillumbah','Yamba','Byron Bay'],
  VIC: ['Melbourne','Geelong','Ballarat','Bendigo','Shepparton','Mildura','Warrnambool','Traralgon','Wodonga','Horsham','Sale','Ararat','Hamilton','Benalla','Wangaratta','Bairnsdale','Echuca','Mornington','Frankston','Dandenong','Ringwood','Box Hill','Williamstown','St Kilda','Phillip Island','Apollo Bay','Lorne','Torquay','Mount Buller','Falls Creek','Bright','Healesville','Yarra Valley','Daylesford','Hepburn Springs','Queenscliff'],
  QLD: ['Brisbane','Gold Coast','Sunshine Coast','Townsville','Cairns','Toowoomba','Rockhampton','Mackay','Bundaberg','Hervey Bay','Gladstone','Maryborough','Nambour','Caloundra','Maroochydore','Noosa','Innisfail','Mount Isa','Emerald','Charleville','Longreach','Roma','Port Douglas','Mission Beach','Airlie Beach','Hamilton Island','Whitsundays','Magnetic Island','Mossman','Palm Cove','Trinity Beach'],
  WA: ['Perth','Fremantle','Rockingham','Mandurah','Bunbury','Geraldton','Kalgoorlie','Albany','Broome','Port Hedland','Karratha','Esperance','Busselton','Margaret River','Exmouth','Carnarvon','Tom Price','Newman','Rottnest Island','Northam','Collie','Harvey','Manjimup','Denmark'],
  SA: ['Adelaide','Mount Gambier','Whyalla','Murray Bridge','Port Augusta','Port Pirie','Victor Harbor','Gawler','Port Lincoln','Millicent','Kangaroo Island','Barossa Valley','McLaren Vale','Clare Valley','Willunga','Strathalbyn','Hahndorf','Tanunda','Nuriootpa','Robe','Beachport','Naracoorte'],
  TAS: ['Hobart','Launceston','Devonport','Burnie','Ulverstone','Queenstown','Strahan','Cradle Mountain','Freycinet','Bicheno','St Helens','St Marys','Swansea','Orford','Port Arthur','Richmond','Ross','Campbell Town','Longford','Evandale','Deloraine','Penguin','Stanley','Smithton','Wynyard'],
  NT: ['Darwin','Alice Springs','Palmerston','Katherine','Tennant Creek','Nhulunbuy','Kakadu','Uluru','Litchfield','Nitmiluk','Jabiru','Yulara'],
  ACT: ['Canberra','Belconnen','Tuggeranong','Woden','Gungahlin','Queanbeyan'],
}

export default function ScraperPanel({ showToast }) {
  const [categories, setCategories]               = useState([])
  const [status, setStatus]                       = useState({ google_places: false, hunter: false })
  const [googleQuota, setGoogleQuota]             = useState(null)
  const [selectedCats, setSelectedCats]           = useState([])
  const [selectedCountries, setSelectedCountries] = useState(['US'])
  const [selectedStates, setSelectedStates]       = useState([])
  const [selectedCities, setSelectedCities]       = useState([])  // empty = any city
  const [customCities, setCustomCities]           = useState('')
  const [hunterCredits, setHunterCredits]         = useState(0)   // 0 = OFF by default
  const [resultsPerCity, setResultsPerCity]       = useState(20)
  const [jobs, setJobs]                           = useState([])
  const [running, setRunning]                     = useState(false)
  const pollRef = useRef(null)

  useEffect(() => {
    axios.get('/api/scraper/categories').then(r => setCategories(r.data)).catch(() => {})
    axios.get('/api/scraper/status').then(r => setStatus(r.data)).catch(() => {})
    axios.get('/api/scraper/google-quota').then(r => setGoogleQuota(r.data)).catch(() => {})
    loadJobs()
  }, [])

  useEffect(() => {
    const hasRunning = jobs.some(j => j.status === 'running' || j.status === 'pending')
    if (hasRunning) { pollRef.current = setInterval(loadJobs, 3000) }
    else { clearInterval(pollRef.current) }
    return () => clearInterval(pollRef.current)
  }, [jobs])

  function loadJobs() { getScrapeJobs().then(setJobs).catch(() => {}) }

  function toggleCat(label) {
    setSelectedCats(p => p.includes(label) ? p.filter(c => c !== label) : [...p, label])
  }

  function toggleCountry(code) {
    setSelectedCountries(p => {
      const next = p.includes(code) ? p.filter(c => c !== code) : [...p, code]
      setSelectedStates(s => s.filter(st => next.some(c => STATES_BY_COUNTRY[c]?.includes(st))))
      setSelectedCities([])
      return next
    })
  }

  function toggleState(s) {
    setSelectedStates(p => {
      const next = p.includes(s) ? p.filter(x => x !== s) : [...p, s]
      // Remove selected cities that belong to a state that was just deselected
      setSelectedCities(c => c.filter(city =>
        next.some(st => (CITIES_BY_STATE[st] || []).includes(city))
      ))
      return next
    })
  }

  function selectAllStates() {
    setSelectedStates(selectedCountries.flatMap(c => STATES_BY_COUNTRY[c] || []))
    setSelectedCities([])
  }

  function toggleCity(city) {
    setSelectedCities(p => p.includes(city) ? p.filter(x => x !== city) : [...p, city])
  }

  function selectAllCities() {
    const all = selectedStates.flatMap(s => CITIES_BY_STATE[s] || [])
    setSelectedCities(all)
  }

  function parseCustomCities() {
    if (!customCities.trim()) return []
    return customCities.split('\n').map(l => l.trim()).filter(l => l.length > 0)
  }

  function estimateRequests() {
    let locs = customLocs.length
    if (selectedStates.length > 0) {
      if (anyCityMode) {
        locs += statesWithCities.flatMap(s => CITIES_BY_STATE[s] || []).length
        const statesWithoutCities = selectedStates.filter(s => !(CITIES_BY_STATE[s] || []).length)
        locs += statesWithoutCities.length
      } else {
        locs += selectedCities.length
      }
    }
    return locs * selectedCats.length * Math.ceil(resultsPerCity / 20)
  }

  async function startScrape() {
    if (!status.google_places) {
      showToast('Add GOOGLE_PLACES_API_KEY to .env first', 'error'); return
    }
    if (selectedCats.length === 0) { showToast('Select at least one business type', 'error'); return }

    const customLocs = parseCustomCities()
    if (selectedStates.length === 0 && customLocs.length === 0) {
      showToast('Select at least one state or enter a custom city', 'error'); return
    }

    setRunning(true)
    try {
      for (const cat of selectedCats) {
        await axios.post('/api/scraper/run', {
          category_label:   cat,
          states:           selectedStates,
          selected_cities:  selectedCities,
          custom_locations: customLocs,
          hunter_credits:   hunterCredits,
          max_results_per_city: resultsPerCity,
        })
      }
      showToast(`Started ${selectedCats.length} search job${selectedCats.length > 1 ? 's' : ''}`, 'success')
      loadJobs()
      axios.get('/api/scraper/google-quota').then(r => setGoogleQuota(r.data)).catch(() => {})
    } catch (e) {
      showToast('Failed to start: ' + (e.response?.data?.detail || e.message), 'error')
    } finally {
      setRunning(false)
    }
  }

  // Which states have a known city list
  const statesWithCities = selectedStates.filter(s => (CITIES_BY_STATE[s] || []).length > 0)
  const anyCityMode      = selectedCities.length === 0
  const customLocs       = parseCustomCities()

  const visibleStates = selectedCountries.flatMap(c => STATES_BY_COUNTRY[c] || [])
  const activeJobs    = jobs.filter(j => j.status === 'running' || j.status === 'pending')
  const doneJobs      = jobs.filter(j => j.status === 'done'    || j.status === 'failed')

  return (
    <div className="scraper-panel">
      <h2>Lead Scraper</h2>
      <p>Search Google Maps for businesses to recruit from, then find their HR contact emails.</p>

      {/* API status pills */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
        <StatusPill label="Google Places" ok={status.google_places}
          okText="Connected" failText="Missing API key — add GOOGLE_PLACES_API_KEY to .env" />
        <StatusPill label="Hunter.io" ok={status.hunter} warn
          okText="Connected — verified emails" failText="Not set — using free website scanner" />
        {googleQuota && status.google_places && (
          <QuotaPill used={googleQuota.used} limit={googleQuota.limit} remaining={googleQuota.remaining} month={googleQuota.month} />
        )}
      </div>

      <div className="scraper-form">

        {/* 1 — Business types */}
        <div>
          <label className="form-label">Business Types</label>
          <div className="checkbox-grid">
            {categories.map(cat => (
              <label key={cat.label} className={`checkbox-item${selectedCats.includes(cat.label) ? ' checked' : ''}`}>
                <input type="checkbox" checked={selectedCats.includes(cat.label)} onChange={() => toggleCat(cat.label)} />
                {cat.label}
              </label>
            ))}
          </div>
        </div>

        {/* 2 — Countries */}
        <div>
          <label className="form-label">Countries</label>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {COUNTRIES.map(c => (
              <button
                key={c.code}
                onClick={() => toggleCountry(c.code)}
                style={{
                  padding: '6px 14px', borderRadius: 6, border: '1px solid',
                  cursor: 'pointer', fontSize: 12, fontWeight: 600,
                  background: selectedCountries.includes(c.code) ? 'var(--gold)' : 'var(--surface2)',
                  color: selectedCountries.includes(c.code) ? 'var(--navy)' : 'var(--text-dim)',
                  borderColor: selectedCountries.includes(c.code) ? 'var(--gold)' : 'var(--border)',
                  transition: 'all 0.15s',
                }}
              >
                {c.label}
              </button>
            ))}
          </div>
        </div>

        {/* 3 — States / Provinces */}
        {visibleStates.length > 0 && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <label className="form-label" style={{ marginBottom: 0 }}>States &amp; Provinces</label>
              <div style={{ display: 'flex', gap: 6 }}>
                <button className="btn btn-secondary btn-sm" onClick={selectAllStates}>All</button>
                <button className="btn btn-secondary btn-sm" onClick={() => { setSelectedStates([]); setSelectedCities([]) }}>Clear</button>
              </div>
            </div>
            {selectedCountries.map(cCode => {
              const sts   = STATES_BY_COUNTRY[cCode] || []
              if (!sts.length) return null
              const label = COUNTRIES.find(c => c.code === cCode)?.label || cCode
              return (
                <div key={cCode} style={{ marginBottom: 10 }}>
                  <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 5 }}>{label}</div>
                  <div className="state-grid">
                    {sts.map(s => (
                      <span key={s}
                        className={`state-tag${selectedStates.includes(s) ? ' selected' : ''}`}
                        onClick={() => toggleState(s)}
                      >{s}</span>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* 4 — City picker (only when states with known cities are selected) */}
        {statesWithCities.length > 0 && (
          <div style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 10,
            padding: '12px 14px',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
              <label className="form-label" style={{ marginBottom: 0 }}>Cities</label>
              <div style={{ display: 'flex', gap: 6 }}>
                {/* Any city button — active when nothing is selected */}
                <button
                  className="btn btn-sm"
                  onClick={() => setSelectedCities([])}
                  style={{
                    background: anyCityMode ? 'var(--gold)' : 'var(--surface2)',
                    color:      anyCityMode ? 'var(--navy)' : 'var(--text-dim)',
                    border:     `1px solid ${anyCityMode ? 'var(--gold)' : 'var(--border)'}`,
                    fontWeight: 600,
                  }}
                >
                  Any city
                </button>
                <button className="btn btn-secondary btn-sm" onClick={selectAllCities}>All</button>
                {!anyCityMode && (
                  <button className="btn btn-secondary btn-sm" onClick={() => setSelectedCities([])}>Clear</button>
                )}
              </div>
            </div>

            {anyCityMode && (
              <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 8 }}>
                Will search all known cities in the selected states. Click a city below to narrow it down.
              </div>
            )}

            {statesWithCities.map(state => (
              <div key={state} style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 5, fontWeight: 600 }}>
                  {state}
                </div>
                <div className="state-grid">
                  {(CITIES_BY_STATE[state] || []).map(city => (
                    <span
                      key={city}
                      className={`state-tag${selectedCities.includes(city) ? ' selected' : ''}`}
                      onClick={() => toggleCity(city)}
                      style={{ fontSize: 11 }}
                    >
                      {city}
                    </span>
                  ))}
                </div>
              </div>
            ))}

            <div style={{ fontSize: 11, color: anyCityMode ? 'var(--text-dim)' : 'var(--gold)', marginTop: 4 }}>
              {anyCityMode
                ? `${statesWithCities.flatMap(s => CITIES_BY_STATE[s] || []).length} cities queued`
                : `${selectedCities.length} city${selectedCities.length !== 1 ? 'ies' : 'y'} selected`}
            </div>
          </div>
        )}

        {/* 5 — Custom cities */}
        <div>
          <label className="form-label">
            Custom Cities{' '}
            <span style={{ fontWeight: 400, color: 'var(--text-dim)', textTransform: 'none', letterSpacing: 0 }}>
              (optional — one per line, e.g. "Miami Beach, FL")
            </span>
          </label>
          <textarea
            className="detail-textarea"
            rows={3}
            placeholder={"Miami Beach, FL\nAspen, CO\nWhistler, BC\nGold Coast, QLD"}
            value={customCities}
            onChange={e => setCustomCities(e.target.value)}
            style={{ fontFamily: 'monospace', fontSize: 12 }}
          />
          {customLocs.length > 0 && (
            <div style={{ fontSize: 11, color: 'var(--gold)', marginTop: 4 }}>
              ✓ {customLocs.length} custom location{customLocs.length !== 1 ? 's' : ''} added
            </div>
          )}
        </div>

        {/* 6 — Hunter.io credits (only shown when Hunter is connected) */}
        {status.hunter && (
          <div style={{
            background: 'var(--surface)',
            border: `1px solid ${hunterCredits > 0 ? '#92400e' : 'var(--border)'}`,
            borderRadius: 10, padding: '12px 16px',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ fontWeight: 600, fontSize: 13 }}>Hunter.io credits for this search</span>
              <span style={{
                fontWeight: 700, fontSize: 14,
                color: hunterCredits === 0 ? 'var(--text-dim)' : '#f59e0b',
                background: hunterCredits === 0 ? 'var(--surface2)' : '#451a03',
                borderRadius: 6, padding: '2px 10px',
              }}>
                {hunterCredits === 0 ? 'OFF — free scraper only' : `${hunterCredits} credit${hunterCredits !== 1 ? 's' : ''}`}
              </span>
            </div>
            <input
              type="range" min={0} max={25} step={1}
              value={hunterCredits}
              onChange={e => setHunterCredits(Number(e.target.value))}
              style={{ width: '100%', accentColor: '#f59e0b' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-dim)', marginTop: 4 }}>
              <span>0 — Free scraper only (no credits used)</span>
              <span style={{ color: hunterCredits > 0 ? '#f59e0b' : 'var(--text-dim)' }}>
                {hunterCredits > 0
                  ? `Uses up to ${hunterCredits} of your monthly credits`
                  : 'Scans company websites for free'}
              </span>
              <span>25</span>
            </div>
          </div>
        )}

        {/* 7 — Results per city */}
        <div>
          <label className="form-label">Results per city: <strong style={{ color: 'var(--gold)' }}>{resultsPerCity}</strong></label>
          <input type="range" min={20} max={60} step={20} value={resultsPerCity}
            onChange={e => setResultsPerCity(Number(e.target.value))}
            style={{ width: '100%', accentColor: 'var(--gold)' }} />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--text-dim)', marginTop: 2 }}>
            <span>20 — quick</span><span>40 — balanced</span><span>60 — thorough</span>
          </div>
        </div>

        {/* Request estimate + start */}
        {selectedCats.length > 0 && (selectedStates.length > 0 || customLocs.length > 0) && (() => {
          const est = estimateRequests()
          const remaining = googleQuota?.remaining ?? Infinity
          const overQuota = est > remaining
          return (
            <div style={{
              background: 'var(--surface)',
              border: `1px solid ${overQuota ? '#7f1d1d' : '#1e3a5f'}`,
              borderRadius: 10, padding: '10px 14px',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12,
            }}>
              <div>
                <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>Requests estimados: </span>
                <span style={{ fontWeight: 700, fontSize: 14, color: overQuota ? '#fca5a5' : 'var(--gold)' }}>
                  ~{est.toLocaleString()} requests
                </span>
                {googleQuota && (
                  <span style={{ fontSize: 11, color: 'var(--text-dim)', marginLeft: 8 }}>
                    ({googleQuota.remaining.toLocaleString()} disponibles este mes)
                  </span>
                )}
                {overQuota && (
                  <div style={{ fontSize: 11, color: '#fca5a5', marginTop: 2 }}>
                    Excede el presupuesto mensual. Reduce ciudades o categorías.
                  </div>
                )}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-dim)', textAlign: 'right', whiteSpace: 'nowrap' }}>
                {Math.ceil(resultsPerCity / 20)} req/ciudad · {
                  anyCityMode
                    ? statesWithCities.flatMap(s => CITIES_BY_STATE[s] || []).length + selectedStates.filter(s => !(CITIES_BY_STATE[s] || []).length).length
                    : selectedCities.length
                }{customLocs.length > 0 ? `+${customLocs.length}` : ''} ciudades · {selectedCats.length} cat.
              </div>
            </div>
          )
        })()}

        {/* Start button */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button className="btn btn-primary" onClick={startScrape} disabled={running} style={{ minWidth: 140 }}>
            {running ? <><span className="spinner" style={{ width: 14, height: 14 }} /> Starting...</> : 'Start Search'}
          </button>
          <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>
            {selectedCats.length} type{selectedCats.length !== 1 ? 's' : ''}
            {selectedStates.length > 0 && ` · ${selectedStates.length} state${selectedStates.length !== 1 ? 's' : ''}`}
            {!anyCityMode && ` · ${selectedCities.length} city${selectedCities.length !== 1 ? 'ies' : 'y'}`}
            {anyCityMode && statesWithCities.length > 0 && ' · any city'}
            {customLocs.length > 0 && ` · ${customLocs.length} custom`}
          </span>
        </div>
      </div>

      {activeJobs.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
            Running <span className="spinner" style={{ width: 12, height: 12 }} />
          </div>
          <div className="jobs-list">{activeJobs.map(j => <JobCard key={j.id} job={j} onCancel={() => cancelJob(j.id).then(loadJobs)} />)}</div>
        </div>
      )}

      {doneJobs.length > 0 && (
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
            Completed
            <button className="btn btn-secondary btn-sm" style={{ marginLeft: 10 }} onClick={loadJobs}>Refresh</button>
          </div>
          <div className="jobs-list">{doneJobs.slice(0, 20).map(j => <JobCard key={j.id} job={j} />)}</div>
        </div>
      )}
    </div>
  )
}

function QuotaPill({ used, limit, remaining, month }) {
  const pct = Math.min(100, Math.round((used / limit) * 100))
  const low = remaining < limit * 0.15
  const color = low ? '#fca5a5' : 'var(--gold)'
  const borderColor = low ? '#7f1d1d' : '#1e3a5f'
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8, background: 'var(--surface)',
      border: `1px solid ${borderColor}`, borderRadius: 8, padding: '8px 12px', fontSize: 12,
    }}>
      <div style={{ width: 8, height: 8, borderRadius: '50%', flexShrink: 0, background: low ? '#dc2626' : '#3b82f6' }} />
      <div>
        <div style={{ fontWeight: 600 }}>Google Places Quota</div>
        <div style={{ color: 'var(--text-dim)', fontSize: 11 }}>
          <span style={{ color }}>{remaining.toLocaleString()} disponibles</span>
          {' '}· {used.toLocaleString()} / {limit.toLocaleString()} usados ({pct}%) · {month}
        </div>
      </div>
    </div>
  )
}

function StatusPill({ label, ok, okText, failText, warn = false }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8, background: 'var(--surface)',
      border: `1px solid ${ok ? '#065f46' : warn ? '#92400e' : '#7f1d1d'}`,
      borderRadius: 8, padding: '8px 12px', fontSize: 12,
    }}>
      <div style={{ width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
        background: ok ? 'var(--converted)' : warn ? '#f59e0b' : '#dc2626' }} />
      <div>
        <div style={{ fontWeight: 600 }}>{label}</div>
        <div style={{ color: 'var(--text-dim)', fontSize: 11 }}>{ok ? okText : failText}</div>
      </div>
    </div>
  )
}

function JobCard({ job, onCancel }) {
  const [cancelling, setCancelling] = useState(false)
  const duration = job.started_at && job.finished_at
    ? Math.round((new Date(job.finished_at) - new Date(job.started_at)) / 1000) + 's' : null

  function handleCancel() {
    setCancelling(true)
    onCancel().finally(() => setCancelling(false))
  }

  return (
    <div className="job-card">
      <div className="job-info">
        <div className="job-title">{job.category} — {job.location}</div>
        <div className="job-meta">
          {job.leads_found > 0 && `${job.leads_found} leads · `}
          {duration && `${duration} · `}
          {job.created_at && new Date(job.created_at).toLocaleString()}
          {job.error && <span style={{ color: '#fca5a5' }}> · {job.error}</span>}
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {job.status === 'running' && onCancel && (
          <button
            onClick={handleCancel}
            disabled={cancelling}
            style={{
              background: '#7f1d1d', color: '#fca5a5', border: '1px solid #991b1b',
              borderRadius: 6, padding: '3px 10px', fontSize: 11, cursor: 'pointer',
              opacity: cancelling ? 0.6 : 1,
            }}
          >
            {cancelling ? 'Stopping…' : '■ Stop'}
          </button>
        )}
        <span className={`job-status job-${job.status}`}>{job.status}</span>
      </div>
    </div>
  )
}
