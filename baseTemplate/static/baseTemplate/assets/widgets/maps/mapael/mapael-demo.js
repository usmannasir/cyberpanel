$(function(){

	// Example #1
	$(".maparea1").mapael({
		map : {
			name : "france_departments"
			, width : 250
		}
	});
	
	// Example #2
	$(".maparea2").mapael({
		map : {
			name : "france_departments"
			, zoom: {
				enabled: true
			}
			, defaultPlot : {
				attrs : {
					opacity : 0.6
				}
			}
		},
		areas: {
			"department-56" : {
				text : {content : "56"}, 
				tooltip: {content : "Morbihan (56)"}
			}
		},
		plots : {
			'paris' : {
				latitude : 48.86, 
				longitude: 2.3444
			},
			'lyon' : {
				type: "circle",
				size:50,
				latitude :45.758888888889, 
				longitude: 4.8413888888889, 
				value : 700000, 
				href : "http://fr.wikipedia.org/wiki/Lyon",
				tooltip: {content : "<span style=\"font-weight:bold;\">City :</span> Lyon"},
				text : {content : "Lyon"}
			},
			'rennes' : {
				type :"square",
				size :20,
				latitude : 48.114166666667, 
				longitude: -1.6808333333333, 
				tooltip: {content : "<span style=\"font-weight:bold;\">City :</span> Rennes"},
				text : {content : "Rennes"},
				href : "http://fr.wikipedia.org/wiki/Rennes"
			}
		}
	});
	
	$('#refreshmaparea2').on('click', function() {
	
		// Update some plots and areas attributes ...
		var updatedOptions = {'areas' : {}, 'plots' : {}};
		updatedOptions.areas["department-56"] = {
			tooltip : {
				content : "Morbihan (56) (2)"
			},
			attrs: {
				fill : "#0088db"
			},
			text : {content : "56 (2)"}
		};
		updatedOptions.plots["rennes"] = {
			tooltip : {
				content : "Rennes (2)"
			},
			attrs: {
				fill : "#f38a03"
			}
			, text : {position : "top"}
			, size : 5
		};
		
		// add some new plots ...
		var newPlots = {
			"Limoge" : {
				latitude : 45.834444,
				longitude : 1.261667,
				text : {content : "Limoge"},
				tooltip : {content : "Limoge"}
			}
			, "Dijon" : {
				size:60,
				latitude : 47.323056,
				longitude : 5.041944,
				text : {
					content : "Dijon",
					position : "left",
					margin : 5
				}
			}
		}
		
		// and delete some others ...
		var deletedPlots = ["paris", "lyon"];
		$(".maparea2").trigger('update', [updatedOptions, newPlots, deletedPlots, {animDuration : 1000}]);
	});
	
	// Example #3
	$(".maparea3").mapael({
		map : {
			name : "france_departments", 
			zoom : {
				enabled : true
			},
			defaultArea: {
				attrs : {
					fill: "#5ba4ff",
					stroke: "#99c7ff",
					cursor: "pointer"
				},
				attrsHover : {
					animDuration:0
				},
				text : {
					attrs : {
						cursor: "pointer",
						"font-size" : 10,
						fill :"#000"
					},
					attrsHover : {
						animDuration : 0
					}
				},
				eventHandlers : {
					click: function(e, id, mapElem, textElem) {
						var newData = {'areas' : {}};
						if (mapElem.originalAttrs.fill == "#5ba4ff") {
							newData.areas[id] = {
								attrs : {
									fill : "#0088db"
								}
							};
						} else {
							newData.areas[id] = {
								attrs : {
									fill : "#5ba4ff"
								}
							};
						}
						$(".maparea3").trigger('update', [newData]);
					}
				}
			}
		},
		areas: {
			"department-29" : {
				text : {content : "dblclick", position : "top"}, 
				attrs : {
					fill :"#0088db"
				},
				tooltip: {content : "FinistÃ¨re (29)"},
				eventHandlers : {
					click: function() {},
					dblclick: function(e, id, mapElem, textElem) {
						var newData = {'areas' : {}};
						if (mapElem.originalAttrs.fill == "#5ba4ff") {
							newData.areas[id] = {
								attrs : {
									fill : "#0088db"
								}
							};
						} else {
							newData.areas[id] = {
								attrs : {
									fill : "#5ba4ff"
								}
							};
						}
						$(".maparea3").trigger('update', [newData, false, false, 0]);
					}
				}
			}
		}
	});	
	
	// Example #4
	$(".maparea4").mapael({
		map : {
			name : "france_departments",
			defaultArea: {
				attrs : {
					stroke : "#fff", 
					"stroke-width" : 1
				},
				attrsHover : {
					"stroke-width" : 2
				}
			}
		},
		legend : {
			area : {
				display : true,
				title :"Population of France by department", 
				labelAttrs : {title : "Hide the matching departments"},
				slices : [
					{
						max :300000, 
						attrs : {
							fill : "#97e766"
						},
						label :"Less than de 300 000 inhabitants"
					},
					{
						min :300000, 
						max :500000, 
						attrs : {
							fill : "#7fd34d"
						},
						label :"Between 100 000 and 500 000 inhabitants"
					},
					{
						min :500000, 
						max :1000000, 
						attrs : {
							fill : "#5faa32"
						},
						label :"Between 500 000 and 1 000 000 inhabitants"
					},
					{
						min :1000000, 
						attrs : {
							fill : "#3f7d1a"
						},
						label :"More than 1 million inhabitants"
					}
				]
			}
		},
		areas: {
			"department-59": {
				value: "2617939",
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Nord (59)</span><br />Population : 2617939"}
			},
			"department-75": {
				value: "2268265",
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Paris (75)</span><br />Population : 2268265"}
			},
			"department-13": {
				value: "2000550",
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Bouches-du-RhÃ´ne (13)</span><br />Population : 2000550"}
			},
			"department-69": {
				value: "1756069",
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">RhÃ´ne (69)</span><br />Population : 1756069"}
			},
			"department-92": {
				value: "1590749",
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Hauts-de-Seine (92)</span><br />Population : 1590749"}
			},
			"department-93": {
				value: "1534895",
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Seine-Saint-Denis (93)</span><br />Population : 1534895"}
			},
			"department-62": {
				value: "1489209",
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Pas-de-Calais (62)</span><br />Population : 1489209"}
			},
			"department-33": {
				value: "1479277",
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Gironde (33)</span><br />Population : 1479277"}
			},
			"department-82": {
				value: "248227",
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Tarn-et-Garonne (82)</span><br />Population : 248227"}
			},
			"department-70": {
				value: "247311",
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Haute-SaÃ´ne (70)</span><br />Population : 247311"}
			},
			"department-36": {
				value: "238261",
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Indre (36)</span><br />Population : 238261"}
			},
			"department-65": {
				value: "237945",
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Hautes-PyrÃ©nÃ©es (65)</span><br />Population : 237945"}
			},
			"department-43": {
				value: "231877",
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Haute-Loire (43)</span><br />Population : 231877"}
			},
			"department-973": {
				value: "231167",
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Guyane (973)</span><br />Population : 231167"}
			},
			"department-58": {
				value: "226997",
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">NiÃ¨vre (58)</span><br />Population : 226997"}
			},
			"department-55": {
				value: "200509",
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Meuse (55)</span><br />Population : 200509"}
			},
			"department-32": {
				value: "195489",
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Gers (32)</span><br />Population : 195489"}
			},
			"department-52": {
				value: "191004",
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Haute-Marne (52)</span><br />Population : 191004"}
			},
			"department-46": {
				value: "181232",
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Lot (46)</span><br />Population : 181232"}
			},
			"department-2B": {
				value: "168869",
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Haute-Corse (2B)</span><br />Population : 168869"}
			},
			"department-04": {
				value: "165155",
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Alpes-de-Haute-Provence (04)</span><br />Population : 165155"}
			},
			"department-09": {
				value: "157582",
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">AriÃ¨ge (09)</span><br />Population : 157582"}
			},
			"department-15": {
				value: "154135",
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Cantal (15)</span><br />Population : 154135"}
			},
			"department-90": {
				value: "146475",
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Territoire de Belfort (90)</span><br />Population : 146475"}
			},
			"department-2A": {
				value: "145998",
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Corse-du-Sud (2A)</span><br />Population : 145998"}
			},
			"department-05": {
				value: "142312",
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Hautes-Alpes (05)</span><br />Population : 142312"}
			},
			"department-23": {
				value: "127919",
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Creuse (23)</span><br />Population : 127919"}
			},
			"department-48": {
				value: "81281",
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">LozÃ¨re (48)</span><br />Population : 81281"}
			}
		}
	});	
	
	// Example #5
	$(".maparea5").mapael({
		map : {
			name : "france_departments",
			defaultPlot: {
				size: 10
			},
			defaultArea : {
				attrsHover: {
					fill: "#343434"
					, stroke: "#5d5d5d"
					, "stroke-width": 1
					, "stroke-linejoin": "round"
				}
			}
		},
		legend : {
			plot :{
				display : true,
				cssClass: 'cityFrance'
				, labelAttrs: {
					fill: "#fff"
				}
				, titleAttrs: {
					fill: "#fff"
				}
				, marginBottom: 20
				, marginLeft : 30
				, hideElemsOnClick : {
					opacity : 0
				}
				, title: "Population of France by city"
				, slices : [
					{
						size: 4,
						type :"circle",
						max :20000, 
						attrs : {
							fill : "#89ff72"
						},
						label :"Less than 20000 inhabitants"
					},
					{
						size: 6,
						type :"circle",
						min :20000, 
						max :100000, 
						attrs : {
							fill : "#fffd72"
						},
						label :"Between 20000 and 100000 inhabitants"
					},
					{
						size: 20,
						type :"circle",
						min :100000, 
						max :200000, 
						attrs : {
							fill : "#ffbd54"
						},
						label :"Between 100000 et  200000 inhabitants"
					},
					{
						size: 40,
						type :"circle",
						min :200000, 
						attrs : {
							fill : "#ff5454"
						},
						label :"More than 200000 inhabitants"
					}
				]
			}
		},
		plots: {
			"town-75056" : {
				value: "2268265",
				latitude: 48.86,
				longitude: 2.3444444444444,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Paris (75056)</span><br />Population : 2268265"}
			},
			"town-13055" : {
				value: "859368",
				latitude: 43.296666666667,
				longitude: 5.3763888888889,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Marseille (13055)</span><br />Population : 859368"}
			},
			"town-69123" : {
				value: "492578",
				latitude: 45.758888888889,
				longitude: 4.8413888888889,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Lyon (69123)</span><br />Population : 492578"}
			},
			"town-31555" : {
				value: "449328",
				latitude: 43.604444444444,
				longitude: 1.4419444444444,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Toulouse (31555)</span><br />Population : 449328"}
			},
			"town-06088" : {
				value: "347105",
				latitude: 43.701944444444,
				longitude: 7.2683333333333,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Nice (06088)</span><br />Population : 347105"}
			},
			"town-44109" : {
				value: "293234",
				latitude: 47.217222222222,
				longitude: -1.5538888888889,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Nantes (44109)</span><br />Population : 293234"}
			},
			"town-67482" : {
				value: "276401",
				latitude: 48.583611111111,
				longitude: 7.7480555555556,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Strasbourg (67482)</span><br />Population : 276401"}
			},
			"town-34172" : {
				value: "260572",
				latitude: 43.611111111111,
				longitude: 3.8766666666667,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Montpellier (34172)</span><br />Population : 260572"}
			},
			"town-33063" : {
				value: "242945",
				latitude: 44.837777777778,
				longitude: -0.57944444444444,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Bordeaux (33063)</span><br />Population : 242945"}
			},
			"town-59350" : {
				value: "234058",
				latitude: 50.631944444444,
				longitude: 3.0575,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Lille (59350)</span><br />Population : 234058"}
			},
			"town-35238" : {
				value: "212939",
				latitude: 48.114166666667,
				longitude: -1.6808333333333,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Rennes (35238)</span><br />Population : 212939"}
			},
			"town-51454" : {
				value: "184011",
				latitude: 49.265277777778,
				longitude: 4.0286111111111,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Reims (51454)</span><br />Population : 184011"}
			},
			"town-76351" : {
				value: "178070",
				latitude: 49.498888888889,
				longitude: 0.12111111111111,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Le Havre (76351)</span><br />Population : 178070"}
			},
			"town-42218" : {
				value: "174566",
				latitude: 45.433888888889,
				longitude: 4.3897222222222,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Saint-Ã‰tienne (42218)</span><br />Population : 174566"}
			},
			"town-83137" : {
				value: "166851",
				latitude: 43.125,
				longitude: 5.9305555555556,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Toulon (83137)</span><br />Population : 166851"}
			},
			"town-38185" : {
				value: "158249",
				latitude: 45.186944444444,
				longitude: 5.7263888888889,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Grenoble (38185)</span><br />Population : 158249"}
			},
			"town-21231" : {
				value: "155233",
				latitude: 47.323055555556,
				longitude: 5.0419444444444,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Dijon (21231)</span><br />Population : 155233"}
			},
			"town-49007" : {
				value: "151957",
				latitude: 47.472777777778,
				longitude: -0.55555555555556,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Angers (49007)</span><br />Population : 151957"}
			},
			"town-72181" : {
				value: "147108",
				latitude: 48.004166666667,
				longitude: 0.19694444444444,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Le Mans (72181)</span><br />Population : 147108"}
			},
			"town-69266" : {
				value: "146729",
				latitude: 45.766111111111,
				longitude: 4.8794444444444,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Villeurbanne (69266)</span><br />Population : 146729"}
			},
			"town-97411" : {
				value: "146489",
				latitude: -20.878888888889,
				longitude: 55.448055555556,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Saint-Denis (97411)</span><br />Population : 146489"}
			},
			"town-29019" : {
				value: "145561",
				latitude: 48.39,
				longitude: -4.4869444444444,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Brest (29019)</span><br />Population : 145561"}
			},
			"town-30189" : {
				value: "145501",
				latitude: 43.836944444444,
				longitude: 4.36,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">NÃ®mes (30189)</span><br />Population : 145501"}
			},
			"town-13001" : {
				value: "144884",
				latitude: 43.527777777778,
				longitude: 5.4455555555556,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Aix-en-Provence (13001)</span><br />Population : 144884"}
			},
			"town-63113" : {
				value: "143669",
				latitude: 45.779722222222,
				longitude: 3.0869444444444,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Clermont-Ferrand (63113)</span><br />Population : 143669"}
			},
			"town-87085" : {
				value: "141540",
				latitude: 45.834444444444,
				longitude: 1.2616666666667,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Limoges (87085)</span><br />Population : 141540"}
			},
			"town-37261" : {
				value: "138268",
				latitude: 47.392777777778,
				longitude: 0.68833333333333,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Tours (37261)</span><br />Population : 138268"}
			},
			"town-80021" : {
				value: "136512",
				latitude: 49.891944444444,
				longitude: 2.2977777777778,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Amiens (80021)</span><br />Population : 136512"}
			},
			"town-57463" : {
				value: "122928",
				latitude: 49.119722222222,
				longitude: 6.1769444444444,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Metz (57463)</span><br />Population : 122928"}
			},
			"town-25056" : {
				value: "121038",
				latitude: 47.242222222222,
				longitude: 6.0213888888889,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">BesanÃ§on (25056)</span><br />Population : 121038"}
			},
			"town-66136" : {
				value: "119536",
				latitude: 42.6975,
				longitude: 2.8947222222222,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Perpignan (66136)</span><br />Population : 119536"}
			},
			"town-45234" : {
				value: "117833",
				latitude: 47.902222222222,
				longitude: 1.9041666666667,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">OrlÃ©ans (45234)</span><br />Population : 117833"}
			},
			"town-92012" : {
				value: "115264",
				latitude: 48.835277777778,
				longitude: 2.2413888888889,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Boulogne-Billancourt (92012)</span><br />Population : 115264"}
			},
			"town-76540" : {
				value: "113461",
				latitude: 49.443055555556,
				longitude: 1.1025,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Rouen (76540)</span><br />Population : 113461"}
			},
			"town-14118" : {
				value: "111949",
				latitude: 49.182222222222,
				longitude: -0.37055555555556,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Caen (14118)</span><br />Population : 111949"}
			},
			"town-68224" : {
				value: "111273",
				latitude: 47.748611111111,
				longitude: 7.3391666666667,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Mulhouse (68224)</span><br />Population : 111273"}
			},
			"town-93066" : {
				value: "107959",
				latitude: 48.935555555556,
				longitude: 2.3538888888889,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Saint-Denis (93066)</span><br />Population : 107959"}
			},
			"town-93066" : {
				value: "107959",
				latitude: 48.935555555556,
				longitude: 2.3538888888889,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Saint-Denis (93066)</span><br />Population : 107959"}
			},
			"town-54395" : {
				value: "107710",
				latitude: 48.692777777778,
				longitude: 6.1836111111111,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Nancy (54395)</span><br />Population : 107710"}
			},
			"town-95018" : {
				value: "104843",
				latitude: 48.947777777778,
				longitude: 2.2475,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Argenteuil (95018)</span><br />Population : 104843"}
			},
			"town-02738" : {
				value: "14320",
				latitude: 49.655833333333,
				longitude: 3.2872222222222,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Tergnier (02738)</span><br />Population : 14320"}
			},
			"town-01004" : {
				value: "14316",
				latitude: 45.958055555556,
				longitude: 5.3577777777778,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">AmbÃ©rieu-en-Bugey (01004)</span><br />Population : 14316"}
			},
			"town-91661" : {
				value: "9825",
				latitude: 48.701388888889,
				longitude: 2.245,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Villebon-sur-Yvette (91661)</span><br />Population : 9825"}
			},
			"town-63014" : {
				value: "9824",
				latitude: 45.750833333333,
				longitude: 3.1108333333333,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">AubiÃ¨re (63014)</span><br />Population : 9824"}
			},
			"town-60282" : {
				value: "9819",
				latitude: 49.187777777778,
				longitude: 2.4161111111111,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Gouvieux (60282)</span><br />Population : 9819"}
			},
			"town-69271" : {
				value: "9813",
				latitude: 45.744444444444,
				longitude: 4.9663888888889,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Chassieu (69271)</span><br />Population : 9813"}
			},
			"town-33366" : {
				value: "9809",
				latitude: 44.994722222222,
				longitude: -0.44583333333333,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Saint-AndrÃ©-de-Cubzac (33366)</span><br />Population : 9809"}
			},
			"town-31451" : {
				value: "9795",
				latitude: 43.458611111111,
				longitude: 2.0041666666667,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Revel (31451)</span><br />Population : 9795"}
			},
			"town-59011" : {
				value: "9775",
				latitude: 50.529444444444,
				longitude: 2.9327777777778,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">AnnÅ“ullin (59011)</span><br />Population : 9775"}
			},
			"town-13069" : {
				value: "9771",
				latitude: 43.631388888889,
				longitude: 5.1505555555556,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">PÃ©lissanne (13069)</span><br />Population : 9771"}
			},
			"town-91122" : {
				value: "9769",
				latitude: 48.696666666667,
				longitude: 2.1613888888889,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Bures-sur-Yvette (91122)</span><br />Population : 9769"}
			},
			"town-02381" : {
				value: "9756",
				latitude: 49.921666666667,
				longitude: 4.0838888888889,
				href : "#",
				tooltip: {content : "<span style=\"font-weight:bold;\">Hirson (02381)</span><br />Population : 9756"}
			}
		}
	});

	
	// Example #6
	$(".maparea6").mapael({
		map : {
			name : "world_countries",
			defaultArea: {
				attrs : {
					stroke : "#fff", 
					"stroke-width" : 1
				}
			}
		},
		legend : {
			area : {
				display : true,
				title :"Population by country", 
				slices : [
					{
						max :5000000, 
						attrs : {
							fill : "#6aafe1"
						},
						label :"Less than de 5000000 inhabitants"
					},
					{
						min :5000000, 
						max :10000000, 
						attrs : {
							fill : "#459bd9"
						},
						label :"Between 5000000 and 10000000 inhabitants"
					},
					{
						min :10000000, 
						max :50000000, 
						attrs : {
							fill : "#2579b5"
						},
						label :"Between 10000000 and 50000000 inhabitants"
					},
					{
						min :50000000, 
						attrs : {
							fill : "#1a527b"
						},
						label :"More than 50 million inhabitants"
					}
				]
			},
			plot :{
				display : true,
				title: "Some cities ..."
				, slices : [
					{
						max :500000, 
						attrs : {
							fill : "#f99200"
						},
						attrsHover :{
							transform : "s1.5",
							"stroke-width" : 1
						}, 
						label :"less than 500 000 inhabitants", 
						size : 10
					},
					{
						min :500000, 
						max :1000000, 
						attrs : {
							fill : "#f99200"
						},
						attrsHover :{
							transform : "s1.5",
							"stroke-width" : 1
						}, 
						label :"Between 500 000 and 1 000 000 inhabitants", 
						size : 20
					},
					{
						min :1000000, 
						attrs : {
							fill : "#f99200"
						},
						attrsHover :{
							transform : "s1.5",
							"stroke-width" : 1
						}, 
						label :"More than 1 million inhabitants", 
						size : 30
					}
				]
			}
		},
		plots : {
			'paris' : {
				latitude :48.86, 
				longitude :2.3444, 
				value : 500000000, 
				tooltip: {content : "Paris<br />Population: 500000000"}
			},
			'newyork' : {
				latitude :40.667, 
				longitude :-73.833, 
				value : 200001, 
				tooltip: {content : "New york<br />Population: 200001"}
			},
			'sydney' : {
				latitude :-33.917, 
				longitude :151.167, 
				value : 600000, 
				tooltip: {content : "Sydney<br />Population: 600000"}
			},
			'brasilia' : {
				latitude :-15.781682, 
				longitude :-47.924195, 
				value : 200000001, 
				tooltip: {content : "Brasilia<br />Population: 200000001"}
			},
			'tokyo': {
				latitude :35.687418, 
				longitude :139.692306, 
				value : 200001, 
				tooltip: {content : "Tokyo<br />Population: 200001"}
			}
		},
		areas: {
			"AF": {
				"value": "35320445",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Afghanistan<\/span><br \/>Population : 35320445"
				}
			},
			"ZA": {
				"value": "50586757",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">South Africa<\/span><br \/>Population : 50586757"
				}
			},
			"AL": {
				"value": "3215988",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Albania<\/span><br \/>Population : 3215988"
				}
			},
			"DZ": {
				"value": "35980193",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Algeria<\/span><br \/>Population : 35980193"
				}
			},
			"DE": {
				"value": "81726000",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Germany<\/span><br \/>Population : 81726000"
				}
			},
			"AD": {
				"value": "86165",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Andorra<\/span><br \/>Population : 86165"
				}
			},
			"AO": {
				"value": "19618432",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Angola<\/span><br \/>Population : 19618432"
				}
			},
			"AG": {
				"value": "89612",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Antigua And Barbuda<\/span><br \/>Population : 89612"
				}
			},
			"SA": {
				"value": "28082541",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Saudi Arabia<\/span><br \/>Population : 28082541"
				}
			},
			"AR": {
				"value": "40764561",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Argentina<\/span><br \/>Population : 40764561"
				}
			},
			"AM": {
				"value": "3100236",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Armenia<\/span><br \/>Population : 3100236"
				}
			},
			"AU": {
				"value": "22620600",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Australia<\/span><br \/>Population : 22620600"
				}
			},
			"AT": {
				"value": "8419000",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Austria<\/span><br \/>Population : 8419000"
				}
			},
			"AZ": {
				"value": "9168000",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Azerbaijan<\/span><br \/>Population : 9168000"
				}
			},
			"BS": {
				"value": "347176",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Bahamas<\/span><br \/>Population : 347176"
				}
			},
			"BH": {
				"value": "1323535",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Bahrain<\/span><br \/>Population : 1323535"
				}
			},
			"BD": {
				"value": "150493658",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Bangladesh<\/span><br \/>Population : 150493658"
				}
			},
			"BB": {
				"value": "273925",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Barbados<\/span><br \/>Population : 273925"
				}
			},
			"BE": {
				"value": "11008000",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Belgium<\/span><br \/>Population : 11008000"
				}
			},
			"BZ": {
				"value": "356600",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Belize<\/span><br \/>Population : 356600"
				}
			},
			"BJ": {
				"value": "9099922",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Benin<\/span><br \/>Population : 9099922"
				}
			},
			"BT": {
				"value": "738267",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Bhutan<\/span><br \/>Population : 738267"
				}
			},
			"BY": {
				"value": "9473000",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Belarus<\/span><br \/>Population : 9473000"
				}
			},
			"MM": {
				"value": "48336763",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Myanmar<\/span><br \/>Population : 48336763"
				}
			},
			"BO": {
				"value": "10088108",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Bolivia, Plurinational State Of<\/span><br \/>Population : 10088108"
				}
			},
			"BA": {
				"value": "3752228",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Bosnia And Herzegovina<\/span><br \/>Population : 3752228"
				}
			},
			"BW": {
				"value": "2030738",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Botswana<\/span><br \/>Population : 2030738"
				}
			},
			"BR": {
				"value": "196655014",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Brazil<\/span><br \/>Population : 196655014"
				}
			},
			"BN": {
				"value": "405938",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Brunei Darussalam<\/span><br \/>Population : 405938"
				}
			},
			"BG": {
				"value": "7476000",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Bulgaria<\/span><br \/>Population : 7476000"
				}
			},
			"BF": {
				"value": "16967845",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Burkina Faso<\/span><br \/>Population : 16967845"
				}
			},
			"BI": {
				"value": "8575172",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Burundi<\/span><br \/>Population : 8575172"
				}
			},
			"KH": {
				"value": "14305183",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Cambodia<\/span><br \/>Population : 14305183"
				}
			},
			"CM": {
				"value": "20030362",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Cameroon<\/span><br \/>Population : 20030362"
				}
			},
			"CA": {
				"value": "34482779",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Canada<\/span><br \/>Population : 34482779"
				}
			},
			"CV": {
				"value": "500585",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Cape Verde<\/span><br \/>Population : 500585"
				}
			},
			"ZW": {
				"value": "12754378",
				"attrs": {
					"href": "#"
				},
				"tooltip": {
					"content": "<span style=\"font-weight:bold;\">Zimbabwe<\/span><br \/>Population : 12754378"
				}
			}
		}
	});
	
	// Example #7
	$(".maparea7").mapael({
		map : {
			name : "usa_states"
		},
		plots: {
			'ny' : {
				latitude: 40.717079,
				longitude: -74.00116,
				tooltip: {content : "New York"}
			},
			'an' : {
				latitude: 61.2108398, 
				longitude: -149.9019557,
				tooltip: {content : "Anchorage"}
			},
			'sf' : {
				latitude: 37.792032,
				longitude: -122.394613,
				tooltip: {content : "San Francisco"}
			},
			'pa' : {
				latitude: 19.493204,
				longitude: -154.8199569,
				tooltip: {content : "Pahoa"}
			}
		}
	});
});