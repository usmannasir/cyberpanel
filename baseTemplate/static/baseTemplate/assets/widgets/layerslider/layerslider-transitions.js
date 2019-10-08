
/*
 * 2D & 3D Transitions for LayerSlider
 *
 * (c) 2011-2014 George Krupa, John Gera & Kreatura Media
 *
 * Plugin web:			http://kreaturamedia.com/
 * Licenses: 			http://codecanyon.net/licenses/
 */



var layerSliderTransitions = {

    /* 2D Transitions */

    t2d : [

        /*
         {
         name : 'Custom 2D transition',	// Name of the transition
         rows : [2,4],					// Number or [minimum,maximum] numbers of rows
         cols : [4,7],					// Number or [minimum,maximum] numbers of columns
         tile : {
         delay : 50,					// Delay of tiles relative to each other in msec
         sequence : 'forward'		// Sequence of the tile transition, can be: 'forward', 'reverse', 'col-forward', 'col-reverse' or 'random'
         },
         transition : {
         type : 'slide',				// Type of the transition, can be: 'slide', 'fade' or 'mixed'
         easing : 'easeInOutQuart',	// Easing of the tile transition
         duration : 1500,			// Duration of the tile transition in msec
         direction : 'left',			// Direction of the tile transition, can be: 'left', 'right', 'top', 'bottom', 'topleft', 'topright', 'bottomleft', 'bottomright' or 'random' (from the 4 main directions)
         scale : .5,					// Scale (integer, must be >= 0)
         rotate : -90,				// Rotate around the Z axis by the given degrees (2D rotation)
         rotateX : 90,				// Rotate around the X axis by the given degrees (3D rotation)
         rotateY : 90				// Rotate around the Y axis by the given degrees (3D rotation)
         }
         },
         */

        /* Sliding transitions: full-tile */

        {
            name : 'Sliding from right',
            rows : 1,
            cols : 1,
            tile : {
                delay : 0,
                sequence : 'forward'
            },
            transition : {
                type : 'slide',
                easing : 'easeInOutQuad',
                duration : 1000,
                direction : 'left'
            }
        },

        {
            name : 'Sliding from left',
            rows : 1,
            cols : 1,
            tile : {
                delay : 0,
                sequence : 'forward'
            },
            transition : {
                type : 'slide',
                easing : 'easeInOutQuad',
                duration : 1000,
                direction : 'right'
            }
        },

        {
            name : 'Sliding from bottom',
            rows : 1,
            cols : 1,
            tile : {
                delay : 0,
                sequence : 'forward'
            },
            transition : {
                type : 'slide',
                easing : 'easeInOutQuad',
                duration : 1000,
                direction : 'top'
            }
        },

        {
            name : 'Sliding from top',
            rows : 1,
            cols : 1,
            tile : {
                delay : 0,
                sequence : 'forward'
            },
            transition : {
                type : 'slide',
                easing : 'easeInOutQuad',
                duration : 1000,
                direction : 'bottom'
            }
        },

        /* Fading transitions */

        {
            name : 'Crossfading',
            rows : 1,
            cols : 1,
            tile : {
                delay : 0,
                sequence : 'forward'
            },
            transition : {
                type : 'fade',
                easing : 'easeInOutQuad',
                duration : 1000,
                direction : 'left'
            }
        },

        {
            name : 'Fading tiles forward',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 30,
                sequence : 'forward'
            },
            transition : {
                type : 'fade',
                easing : 'easeOutQuart',
                duration : 1000,
                direction : 'left'
            }
        },

        {
            name : 'Fading tiles reverse',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 30,
                sequence : 'reverse'
            },
            transition : {
                type : 'fade',
                easing : 'easeOutQuart',
                duration : 1000,
                direction : 'left'
            }
        },

        {
            name : 'Fading tiles col-forward',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 30,
                sequence : 'col-forward'
            },
            transition : {
                type : 'fade',
                easing : 'easeOutQuart',
                duration : 1000,
                direction : 'left'
            }
        },

        {
            name : 'Fading tiles col-reverse',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 30,
                sequence : 'col-reverse'
            },
            transition : {
                type : 'fade',
                easing : 'easeOutQuart',
                duration : 1000,
                direction : 'left'
            }
        },

        {
            name : 'Fading tiles (random)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 30,
                sequence : 'random'
            },
            transition : {
                type : 'fade',
                easing : 'easeOutQuart',
                duration : 1000,
                direction : 'left'
            }
        },

        {
            name : 'Smooth fading from right',
            rows : 1,
            cols : 35,
            tile : {
                delay : 25,
                sequence : 'reverse'
            },
            transition : {
                type : 'fade',
                easing : 'linear',
                duration : 750,
                direction : 'left'
            }
        },

        {
            name : 'Smooth fading from left',
            rows : 1,
            cols : 35,
            tile : {
                delay : 25,
                sequence : 'forward'
            },
            transition : {
                type : 'fade',
                easing : 'easeInOutQuart',
                duration : 750,
                direction : 'left'
            }
        },

        {
            name : 'Smooth fading from bottom',
            rows : 35,
            cols : 1,
            tile : {
                delay : 25,
                sequence : 'col-reverse'
            },
            transition : {
                type : 'fade',
                easing : 'easeInOutQuart',
                duration : 750,
                direction : 'left'
            }
        },

        {
            name : 'Smooth fading from top',
            rows : 35,
            cols : 1,
            tile : {
                delay : 25,
                sequence : 'col-forward'
            },
            transition : {
                type : 'fade',
                easing : 'easeInOutQuart',
                duration : 750,
                direction : 'left'
            }
        },

        /* Sliding transitions: smooth */

        {
            name : 'Smooth sliding from right',
            rows : 1,
            cols : 25,
            tile : {
                delay : 30,
                sequence : 'reverse'
            },
            transition : {
                type : 'slide',
                easing : 'easeInOutQuart',
                duration : 350,
                direction : 'left'
            }
        },

        {
            name : 'Smooth sliding from left',
            rows : 1,
            cols : 25,
            tile : {
                delay : 30,
                sequence : 'forward'
            },
            transition : {
                type : 'slide',
                easing : 'easeInOutQuart',
                duration : 350,
                direction : 'right'
            }
        },

        {
            name : 'Smooth sliging from bottom',
            rows : 25,
            cols : 1,
            tile : {
                delay : 30,
                sequence : 'col-reverse'
            },
            transition : {
                type : 'slide',
                easing : 'easeInOutQuart',
                duration : 350,
                direction : 'top'
            }
        },

        {
            name : 'Smooth sliding from top',
            rows : 25,
            cols : 1,
            tile : {
                delay : 30,
                sequence : 'col-forward'
            },
            transition : {
                type : 'slide',
                easing : 'easeInOutQuart',
                duration : 350,
                direction : 'bottom'
            }
        },

        /* Sliding transitions: tiles */

        {
            name : 'Sliding tiles to right (random)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 50,
                sequence : 'random'
            },
            transition : {
                type : 'slide',
                easing : 'easeOutQuart',
                duration : 500,
                direction : 'right'
            }
        },

        {
            name : 'Sliding tiles to left (random)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 50,
                sequence : 'random'
            },
            transition : {
                type : 'slide',
                easing : 'easeOutQuart',
                duration : 500,
                direction : 'left'
            }
        },

        {
            name : 'Sliding tiles to bottom (random)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 50,
                sequence : 'random'
            },
            transition : {
                type : 'slide',
                easing : 'easeOutQuart',
                duration : 500,
                direction : 'bottom'
            }
        },

        {
            name : 'Sliding tiles to top (random)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 50,
                sequence : 'random'
            },
            transition : {
                type : 'slide',
                easing : 'easeOutQuart',
                duration : 500,
                direction : 'top'
            }
        },

        {
            name : 'Sliding random tiles to random directions',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 50,
                sequence : 'random'
            },
            transition : {
                type : 'slide',
                easing : 'easeOutQuart',
                duration : 500,
                direction : 'random'
            }
        },

        /* Sliding transitions: rows */

        {
            name : 'Sliding rows to right (forward)',
            rows : [7,11],
            cols : 1,
            tile : {
                delay : 100,
                sequence : 'forward'
            },
            transition : {
                type : 'slide',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'right'
            }
        },

        {
            name : 'Sliding rows to right (reverse)',
            rows : [7,11],
            cols : 1,
            tile : {
                delay : 100,
                sequence : 'reverse'
            },
            transition : {
                type : 'slide',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'right'
            }
        },

        {
            name : 'Sliding rows to right (random)',
            rows : [7,11],
            cols : 1,
            tile : {
                delay : 100,
                sequence : 'random'
            },
            transition : {
                type : 'slide',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'right'
            }
        },

        {
            name : 'Sliding rows to left (forward)',
            rows : [7,11],
            cols : 1,
            tile : {
                delay : 100,
                sequence : 'forward'
            },
            transition : {
                type : 'slide',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'left'
            }
        },

        {
            name : 'Sliding rows to left (reverse)',
            rows : [7,11],
            cols : 1,
            tile : {
                delay : 100,
                sequence : 'reverse'
            },
            transition : {
                type : 'slide',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'left'
            }
        },

        {
            name : 'Sliding rows to left (random)',
            rows : [7,11],
            cols : 1,
            tile : {
                delay : 100,
                sequence : 'random'
            },
            transition : {
                type : 'slide',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'left'
            }
        },

        {
            name : 'Sliding rows from top to bottom (forward)',
            rows : [7,11],
            cols : 1,
            tile : {
                delay : 100,
                sequence : 'forward'
            },
            transition : {
                type : 'slide',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'bottom'
            }
        },

        {
            name : 'Sliding rows from top to bottom (random)',
            rows : [7,11],
            cols : 1,
            tile : {
                delay : 100,
                sequence : 'random'
            },
            transition : {
                type : 'slide',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'bottom'
            }
        },

        {
            name : 'Sliding rows from bottom to top (reverse)',
            rows : [7,11],
            cols : 1,
            tile : {
                delay : 100,
                sequence : 'reverse'
            },
            transition : {
                type : 'slide',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'top'
            }
        },

        {
            name : 'Sliding rows from bottom to top (random)',
            rows : [7,11],
            cols : 1,
            tile : {
                delay : 100,
                sequence : 'random'
            },
            transition : {
                type : 'slide',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'top'
            }
        },

        /* Sliding transitions: columns */

        {
            name : 'Sliding columns to bottom (forward)',
            rows : 1,
            cols : [12,16],
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            transition : {
                type : 'slide',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'bottom'
            }
        },

        {
            name : 'Sliding columns to bottom (reverse)',
            rows : 1,
            cols : [12,16],
            tile : {
                delay : 75,
                sequence : 'reverse'
            },
            transition : {
                type : 'slide',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'bottom'
            }
        },

        {
            name : 'Sliding columns to bottom (random)',
            rows : 1,
            cols : [12,16],
            tile : {
                delay : 75,
                sequence : 'random'
            },
            transition : {
                type : 'slide',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'bottom'
            }
        },

        {
            name : 'Sliding columns to top (forward)',
            rows : 1,
            cols : [12,16],
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            transition : {
                type : 'slide',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'top'
            }
        },

        {
            name : 'Sliding columns to top (reverse)',
            rows : 1,
            cols : [12,16],
            tile : {
                delay : 75,
                sequence : 'reverse'
            },
            transition : {
                type : 'slide',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'top'
            }
        },

        {
            name : 'Sliding columns to top (random)',
            rows : 1,
            cols : [12,16],
            tile : {
                delay : 75,
                sequence : 'random'
            },
            transition : {
                type : 'slide',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'top'
            }
        },

        {
            name : 'Sliding columns from left to right (forward)',
            rows : 1,
            cols : [12,16],
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            transition : {
                type : 'slide',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'right'
            }
        },

        {
            name : 'Sliding columns from left to right (random)',
            rows : 1,
            cols : [12,16],
            tile : {
                delay : 75,
                sequence : 'random'
            },
            transition : {
                type : 'slide',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'right'
            }
        },

        {
            name : 'Sliding columns from right to left (reverse)',
            rows : 1,
            cols : [12,16],
            tile : {
                delay : 75,
                sequence : 'reverse'
            },
            transition : {
                type : 'slide',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'left'
            }
        },

        {
            name : 'Sliding columns from right to left (random)',
            rows : 1,
            cols : [12,16],
            tile : {
                delay : 75,
                sequence : 'random'
            },
            transition : {
                type : 'slide',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'left'
            }
        },

        /* Fading and sliding transitions: tiles */

        {
            name : 'Fading and sliding tiles to right (random)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 50,
                sequence : 'random'
            },
            transition : {
                type : 'mixed',
                easing : 'easeOutQuart',
                duration : 500,
                direction : 'right'
            }
        },

        {
            name : 'Fading and sliding tiles to left (random)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 50,
                sequence : 'random'
            },
            transition : {
                type : 'mixed',
                easing : 'easeOutQuart',
                duration : 500,
                direction : 'left'
            }
        },

        {
            name : 'Fading and sliding tiles to bottom (random)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 50,
                sequence : 'random'
            },
            transition : {
                type : 'mixed',
                easing : 'easeOutQuart',
                duration : 500,
                direction : 'bottom'
            }
        },

        {
            name : 'Fading and sliding tiles to top (random)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 50,
                sequence : 'random'
            },
            transition : {
                type : 'mixed',
                easing : 'easeOutQuart',
                duration : 500,
                direction : 'top'
            }
        },

        {
            name : 'Fading and sliding random tiles to random directions',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 50,
                sequence : 'random'
            },
            transition : {
                type : 'mixed',
                easing : 'easeOutQuart',
                duration : 500,
                direction : 'random'
            }
        },

        {
            name : 'Fading and sliding tiles from top-left (forward)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 50,
                sequence : 'forward'
            },
            transition : {
                type : 'mixed',
                easing : 'easeOutQuart',
                duration : 500,
                direction : 'topleft'
            }
        },

        {
            name : 'Fading and sliding tiles from bottom-right (reverse)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 50,
                sequence : 'reverse'
            },
            transition : {
                type : 'mixed',
                easing : 'easeOutQuart',
                duration : 500,
                direction : 'bottomright'
            }
        },

        {
            name : 'Fading and sliding tiles from top-right (random)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 50,
                sequence : 'random'
            },
            transition : {
                type : 'mixed',
                easing : 'easeOutQuart',
                duration : 500,
                direction : 'topright'
            }
        },

        {
            name : 'Fading and sliding tiles from bottom-left (random)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 50,
                sequence : 'random'
            },
            transition : {
                type : 'mixed',
                easing : 'easeOutQuart',
                duration : 500,
                direction : 'bottomleft'
            }
        },

        /* Fading and sliding transitions: rows */

        {
            name : 'Fading and sliding rows to right (forward)',
            rows : [7,11],
            cols : 1,
            tile : {
                delay : 100,
                sequence : 'forward'
            },
            transition : {
                type : 'mixed',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'right'
            }
        },

        {
            name : 'Fading and sliding rows to right (reverse)',
            rows : [7,11],
            cols : 1,
            tile : {
                delay : 100,
                sequence : 'reverse'
            },
            transition : {
                type : 'mixed',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'right'
            }
        },

        {
            name : 'Fading and sliding rows to right (random)',
            rows : [7,11],
            cols : 1,
            tile : {
                delay : 100,
                sequence : 'random'
            },
            transition : {
                type : 'mixed',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'right'
            }
        },

        {
            name : 'Fading and sliding rows to left (forward)',
            rows : [7,11],
            cols : 1,
            tile : {
                delay : 100,
                sequence : 'forward'
            },
            transition : {
                type : 'mixed',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'left'
            }
        },

        {
            name : 'Fading and sliding rows to left (reverse)',
            rows : [7,11],
            cols : 1,
            tile : {
                delay : 100,
                sequence : 'reverse'
            },
            transition : {
                type : 'mixed',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'left'
            }
        },

        {
            name : 'Fading and sliding rows to left (random)',
            rows : [7,11],
            cols : 1,
            tile : {
                delay : 100,
                sequence : 'random'
            },
            transition : {
                type : 'mixed',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'left'
            }
        },

        {
            name : 'Fading and sliding rows from top to bottom (forward)',
            rows : [7,11],
            cols : 1,
            tile : {
                delay : 100,
                sequence : 'forward'
            },
            transition : {
                type : 'mixed',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'bottom'
            }
        },

        {
            name : 'Fading and sliding rows from top to bottom (random)',
            rows : [7,11],
            cols : 1,
            tile : {
                delay : 100,
                sequence : 'random'
            },
            transition : {
                type : 'mixed',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'bottom'
            }
        },

        {
            name : 'Fading and sliding rows from bottom to top (reverse)',
            rows : [7,11],
            cols : 1,
            tile : {
                delay : 100,
                sequence : 'reverse'
            },
            transition : {
                type : 'mixed',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'top'
            }
        },

        {
            name : 'Fading and sliding rows from bottom to top (random)',
            rows : [7,11],
            cols : 1,
            tile : {
                delay : 100,
                sequence : 'random'
            },
            transition : {
                type : 'mixed',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'top'
            }
        },

        /* Fading and sliding transitions: columns */

        {
            name : 'Fading and sliding columns to bottom (forward)',
            rows : 1,
            cols : [12,16],
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            transition : {
                type : 'mixed',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'bottom'
            }
        },

        {
            name : 'Fading and sliding columns to bottom (reverse)',
            rows : 1,
            cols : [12,16],
            tile : {
                delay : 75,
                sequence : 'reverse'
            },
            transition : {
                type : 'mixed',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'bottom'
            }
        },

        {
            name : 'Fading and sliding columns to bottom (random)',
            rows : 1,
            cols : [12,16],
            tile : {
                delay : 75,
                sequence : 'random'
            },
            transition : {
                type : 'mixed',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'bottom'
            }
        },

        {
            name : 'Fading and sliding columns to top (forward)',
            rows : 1,
            cols : [12,16],
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            transition : {
                type : 'mixed',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'top'
            }
        },

        {
            name : 'Fading and sliding columns to top (reverse)',
            rows : 1,
            cols : [12,16],
            tile : {
                delay : 75,
                sequence : 'reverse'
            },
            transition : {
                type : 'mixed',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'top'
            }
        },

        {
            name : 'Fading and sliding columns to top (random)',
            rows : 1,
            cols : [12,16],
            tile : {
                delay : 75,
                sequence : 'random'
            },
            transition : {
                type : 'mixed',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'top'
            }
        },

        {
            name : 'Fading and sliding columns from left to right (forward)',
            rows : 1,
            cols : [12,16],
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            transition : {
                type : 'mixed',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'right'
            }
        },

        {
            name : 'Fading and sliding columns from left to right (random)',
            rows : 1,
            cols : [12,16],
            tile : {
                delay : 75,
                sequence : 'random'
            },
            transition : {
                type : 'mixed',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'right'
            }
        },

        {
            name : 'Fading and sliding columns from right to left (reverse)',
            rows : 1,
            cols : [12,16],
            tile : {
                delay : 75,
                sequence : 'reverse'
            },
            transition : {
                type : 'mixed',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'left'
            }
        },

        {
            name : 'Fading and sliding columns from right to left (random)',
            rows : 1,
            cols : [12,16],
            tile : {
                delay : 75,
                sequence : 'random'
            },
            transition : {
                type : 'mixed',
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'left'
            }
        },

        // IMPROVEMENT v4.5.0 added new 2D transitions with rotate and / or scale

        {
            name : 'Carousel',
            rows : 1,
            cols : 1,
            tile : {
                delay : 0,
                sequence : 'forward'
            },
            transition : {
                type : 'mixed',
                easing : 'easeInOutQuad',
                duration : 750,
                direction : 'left',
                scale : .5
            }
        },

        {
            name : 'Carousel rows',
            rows : 4,
            cols : 1,
            tile : {
                delay : 50,
                sequence : 'forward'
            },
            transition : {
                type : 'mixed',
                easing : 'easeInOutQuad',
                duration : 750,
                direction : 'left',
                scale : .5
            }
        },

        {
            name : 'Carousel cols',
            rows : 1,
            cols : 4,
            tile : {
                delay : 50,
                sequence : 'forward'
            },
            transition : {
                type : 'mixed',
                easing : 'easeInOutQuad',
                duration : 750,
                direction : 'left',
                scale : .5
            }
        },

        {
            name : 'Carousel tiles horizontal',
            rows : 3,
            cols : 4,
            tile : {
                delay : 35,
                sequence : 'forward'
            },
            transition : {
                type : 'mixed',
                easing : 'easeInOutQuad',
                duration : 750,
                direction : 'left',
                scale : .5,
                rotateY : 90
            }
        },

        {
            name : 'Carousel tiles vertical',
            rows : 3,
            cols : 4,
            tile : {
                delay : 35,
                sequence : 'forward'
            },
            transition : {
                type : 'mixed',
                easing : 'easeInOutQuad',
                duration : 750,
                direction : 'top',
                scale : .5,
                rotateX : -90
            }
        },

        {
            name : 'Carousel-mirror tiles horizontal',
            rows : 3,
            cols : 4,
            tile : {
                delay : 15,
                sequence : 'forward'
            },
            transition : {
                type : 'mixed',
                easing : 'easeInOutQuad',
                duration : 750,
                direction : 'left',
                scale : .5,
                rotateY : 90
            }
        },

        {
            name : 'Carousel-mirror tiles vertical',
            rows : 3,
            cols : 4,
            tile : {
                delay : 15,
                sequence : 'forward'
            },
            transition : {
                type : 'mixed',
                easing : 'easeInOutQuad',
                duration : 750,
                direction : 'top',
                scale : .5,
                rotateX : -90
            }
        },
        {
            name : 'Carousel mirror rows',
            rows : 4,
            cols : 1,
            tile : {
                delay : 50,
                sequence : 'forward'
            },
            transition : {
                type : 'mixed',
                easing : 'easeInOutQuad',
                duration : 750,
                direction : 'right',
                scale : .5
            }
        },

        {
            name : 'Carousel mirror cols',
            rows : 1,
            cols : 4,
            tile : {
                delay : 50,
                sequence : 'forward'
            },
            transition : {
                type : 'mixed',
                easing : 'easeInOutQuad',
                duration : 750,
                direction : 'left',
                scale : .5
            }
        },

        {
            name : 'Turning tile from left',
            rows : 1,
            cols : 1,
            tile : {
                delay : 0,
                sequence : 'forward'
            },
            transition : {
                type : 'slide',
                easing : 'easeOutQuart',
                duration : 750,
                direction : 'right',
                rotateY : 90
            }
        },

        {
            name : 'Turning tile from right',
            rows : 1,
            cols : 1,
            tile : {
                delay : 0,
                sequence : 'forward'
            },
            transition : {
                type : 'slide',
                easing : 'easeOutQuart',
                duration : 750,
                direction : 'left',
                rotateY : -90
            }
        },

        {
            name : 'Turning tile from top',
            rows : 1,
            cols : 1,
            tile : {
                delay : 0,
                sequence : 'forward'
            },
            transition : {
                type : 'slide',
                easing : 'easeOutQuart',
                duration : 750,
                direction : 'bottom',
                rotateX : -90
            }
        },

        {
            name : 'Turning tile from bottom',
            rows : 1,
            cols : 1,
            tile : {
                delay : 0,
                sequence : 'forward'
            },
            transition : {
                type : 'slide',
                easing : 'easeOutQuart',
                duration : 750,
                direction : 'top',
                rotateX : 90
            }
        },

        {
            name : 'Turning tiles from left',
            rows : [3,4],
            cols : [3,4],
            tile : {
                delay : 55,
                sequence : 'forward'
            },
            transition : {
                type : 'fade',
                easing : 'easeOutQuart',
                duration : 750,
                direction : 'left',
                rotateY : 90
            }
        },

        {
            name : 'Turning tiles from right',
            rows : [3,4],
            cols : [3,4],
            tile : {
                delay : 55,
                sequence : 'reverse'
            },
            transition : {
                type : 'fade',
                easing : 'easeOutQuart',
                duration : 750,
                direction : 'left',
                rotateY : -90
            }
        },

        {
            name : 'Turning tiles from top',
            rows : [3,4],
            cols : [3,4],
            tile : {
                delay : 55,
                sequence : 'forward'
            },
            transition : {
                type : 'fade',
                easing : 'easeOutQuart',
                duration : 750,
                direction : 'left',
                rotateX : -90
            }
        },

        {
            name : 'Turning tiles from bottom',
            rows : [3,4],
            cols : [3,4],
            tile : {
                delay : 55,
                sequence : 'reverse'
            },
            transition : {
                type : 'fade',
                easing : 'easeOutQuart',
                duration : 750,
                direction : 'left',
                rotateX : 90
            }
        },

        {
            name : 'Turning rows from top',
            rows : [6,12],
            cols : 1,
            tile : {
                delay : 55,
                sequence : 'forward'
            },
            transition : {
                type : 'fade',
                easing : 'easeOutQuart',
                duration : 750,
                direction : 'left',
                rotateX : 90
            }
        },

        {
            name : 'Turning rows from bottom',
            rows : [6,12],
            cols : 1,
            tile : {
                delay : 55,
                sequence : 'reverse'
            },
            transition : {
                type : 'fade',
                easing : 'easeOutQuart',
                duration : 750,
                direction : 'left',
                rotateX : -90
            }
        },

        {
            name : 'Turning cols from left',
            rows : 1,
            cols : [6,12],
            tile : {
                delay : 55,
                sequence : 'forward'
            },
            transition : {
                type : 'fade',
                easing : 'easeOutQuart',
                duration : 750,
                direction : 'left',
                rotateY : -90
            }
        },

        {
            name : 'Turning cols from right',
            rows : 1,
            cols : [6,12],
            tile : {
                delay : 55,
                sequence : 'reverse'
            },
            transition : {
                type : 'fade',
                easing : 'easeOutQuart',
                duration : 750,
                direction : 'left',
                rotateY : 90
            }
        },

        {
            name : 'Flying rows from left',
            rows : [3,10],
            cols : 1,
            tile : {
                delay : 55,
                sequence : 'forward'
            },
            transition : {
                type : 'fade',
                easing : 'easeOutQuart',
                duration : 750,
                direction : 'left',
                rotateY : 90
            }
        },

        {
            name : 'Flying rows from right',
            rows : [3,10],
            cols : 1,
            tile : {
                delay : 55,
                sequence : 'reverse'
            },
            transition : {
                type : 'fade',
                easing : 'easeOutQuart',
                duration : 750,
                direction : 'left',
                rotateY : -90
            }
        },

        {
            name : 'Flying cols from top',
            rows : 1,
            cols : [3,10],
            tile : {
                delay : 55,
                sequence : 'forward'
            },
            transition : {
                type : 'fade',
                easing : 'easeOutQuart',
                duration : 750,
                direction : 'left',
                rotateX : -90
            }
        },

        {
            name : 'Flying cols from bottom',
            rows : 1,
            cols : [3,10],
            tile : {
                delay : 55,
                sequence : 'reverse'
            },
            transition : {
                type : 'fade',
                easing : 'easeOutQuart',
                duration : 750,
                direction : 'left',
                rotateX : 90
            }
        },

        {
            name : 'Flying and rotating tile from left',
            rows : 1,
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            transition : {
                type : 'mixed',
                easing : 'easeOutQuart',
                duration : 750,
                direction : 'right',
                scale : .1,
                rotate : -90,
                rotateY : 90
            }
        },

        {
            name : 'Flying and rotating tile from right',
            rows : 1,
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            transition : {
                type : 'mixed',
                easing : 'easeOutQuart',
                duration : 750,
                direction : 'left',
                scale : .1,
                rotate : 90,
                rotateY : -90
            }
        },

        {
            name : 'Flying and rotating tiles from left',
            rows : [3,4],
            cols : [3,4],
            tile : {
                delay : 55,
                sequence : 'forward'
            },
            transition : {
                type : 'mixed',
                easing : 'easeOutQuart',
                duration : 750,
                direction : 'right',
                rotate : -45
            }
        },

        {
            name : 'Flying and rotating tiles from right',
            rows : [3,4],
            cols : [3,4],
            tile : {
                delay : 55,
                sequence : 'forward'
            },
            transition : {
                type : 'mixed',
                easing : 'easeOutQuart',
                duration : 750,
                direction : 'left',
                rotate : -45
            }
        },

        {
            name : 'Flying and rotating tiles from random',
            rows : [3,4],
            cols : [3,4],
            tile : {
                delay : 55,
                sequence : 'random'
            },
            transition : {
                type : 'mixed',
                easing : 'easeOutQuart',
                duration : 750,
                direction : 'random',
                rotate : -45
            }
        },

        {
            name : 'Scaling tile in',
            rows : 1,
            cols : 1,
            tile : {
                delay : 0,
                sequence : 'forward'
            },
            transition : {
                type : 'fade',
                easing : 'easeOutQuart',
                duration : 1500,
                direction : 'left',
                scale : .8
            }
        },

        {
            name : 'Scaling tile from out',
            rows : 1,
            cols : 1,
            tile : {
                delay : 0,
                sequence : 'forward'
            },
            transition : {
                type : 'fade',
                easing : 'easeInOutQuart',
                duration : 1500,
                direction : 'left',
                scale : 1.2
            }
        },

        {
            name : 'Scaling tiles random',
            rows : [3,4],
            cols : [3,4],
            tile : {
                delay : 35,
                sequence : 'random'
            },
            transition : {
                type : 'fade',
                easing : 'easeOutQuart',
                duration : 750,
                direction : 'left',
                scale : .1
            }
        },

        {
            name : 'Scaling tiles from out random',
            rows : [3,4],
            cols : [3,4],
            tile : {
                delay : 35,
                sequence : 'random'
            },
            transition : {
                type : 'fade',
                easing : 'easeOutQuart',
                duration : 750,
                direction : 'left',
                scale : 2
            }
        },

        {
            name : 'Scaling in and rotating tiles random',
            rows : [3,4],
            cols : [3,4],
            tile : {
                delay : 35,
                sequence : 'random'
            },
            transition : {
                type : 'fade',
                easing : 'easeOutQuart',
                duration : 750,
                direction : 'left',
                scale : .1,
                rotate : 90
            }
        },

        {
            name : 'Scaling and rotating tiles from out random',
            rows : [3,4],
            cols : [3,4],
            tile : {
                delay : 35,
                sequence : 'random'
            },
            transition : {
                type : 'fade',
                easing : 'easeOutQuart',
                duration : 750,
                direction : 'left',
                scale : 2,
                rotate : -90
            }
        },

        {
            name : 'Mirror-sliding tiles diagonal',
            rows : 3,
            cols : 4,
            tile : {
                delay : 15,
                sequence : 'forward'
            },
            transition : {
                type : 'slide',
                easing : 'easeInOutQuart',
                duration : 850,
                direction : 'topright'
            }
        },

        {
            name : 'Mirror-sliding rows horizontal',
            rows : 6,
            cols : 1,
            tile : {
                delay : 0,
                sequence : 'forward'
            },
            transition : {
                type : 'mixed',
                easing : 'easeOutQuart',
                duration : 750,
                direction : 'left'
            }
        },

        {
            name : 'Mirror-sliding rows vertical',
            rows : 6,
            cols : 1,
            tile : {
                delay : 0,
                sequence : 'forward'
            },
            transition : {
                type : 'mixed',
                easing : 'easeOutQuart',
                duration : 750,
                direction : 'top'
            }
        },

        {
            name : 'Mirror-sliding cols horizontal',
            rows : 1,
            cols : 8,
            tile : {
                delay : 0,
                sequence : 'forward'
            },
            transition : {
                type : 'mixed',
                easing : 'easeOutQuart',
                duration : 750,
                direction : 'left'
            }
        },

        {
            name : 'Mirror-sliding cols vertical',
            rows : 1,
            cols : 8,
            tile : {
                delay : 0,
                sequence : 'forward'
            },
            transition : {
                type : 'mixed',
                easing : 'easeOutQuart',
                duration : 750,
                direction : 'top'
            }
        }
    ],

    /* 3D Transitions */

    t3d : [

        /*
         {
         name : 'Custom 3D transition',	// Name of the transition
         rows : [2,4],					// Number or [minimum,maximum] numbers of rows
         cols : [4,7],					// Number or [minimum,maximum] numbers of columns
         tile : {
         delay : 75,					// Delay of tiles relative to each other in msec
         sequence : 'forward'		// Sequence of the tile transition, can be: 'forward', 'reverse', 'col-forward', 'col-reverse' or 'random'
         },
         // Before animation - not required!
         before : {
         transition : {
         scale3d : .95			// Transitions, can be: scale3d, rotateX, rotateY
         },
         duration : 450,				// Duration of the tile transition in msec
         easing : 'easeInOutQuint'	// Easing of the tile transition
         },
         // Animation - required!
         animation : {
         transition : {
         rotateY: 180			// Transitions, can be: scale3d, rotateX, rotateY
         },
         duration : 1000,			// Duration of the tile transition in msec
         easing : 'easeInOutBack',	// Easing of the tile transition
         direction : 'horizontal'
         },
         // After animation - not required!
         after : {
         duration : 350,				// Duration of the tile transition in msec
         easing : 'easeInOutBack'	// Easing of the tile transition
         }
         },
         */

        // Spinning transitions (180deg, thin depth);

        {
            name : 'Spinning tile to right (180&#176;)',
            rows : 1,
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            animation : {
                transition : {
                    rotateY: 91
                },
                easing : 'easeInQuart',
                duration : 1000,
                direction : 'horizontal'
            },
            after : {
                transition : {
                    rotateY: 180
                },
                easing : 'easeOutQuart',
                duration : 1000,
                direction : 'horizontal'
            }
        },

        {
            name : 'Spinning tile to left (180&#176;)',
            rows : 1,
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            animation : {
                transition : {
                    rotateY: -91
                },
                easing : 'easeInQuart',
                duration : 1000,
                direction : 'horizontal'
            },
            after : {
                transition : {
                    rotateY: -180
                },
                easing : 'easeOutQuart',
                duration : 1000,
                direction : 'horizontal'
            }
        },

        {
            name : 'Spinning tile to bottom (180&#176;)',
            rows : 1,
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            animation : {
                transition : {
                    rotateX: -91
                },
                easing : 'easeInQuart',
                duration : 800,
                direction : 'vertical'
            },
            after : {
                transition : {
                    rotateX: -180
                },
                easing : 'easeOutQuart',
                duration : 800,
                direction : 'vertical'
            }
        },

        {
            name : 'Spinning tile to top (180&#176;)',
            rows : 1,
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            animation : {
                transition : {
                    rotateX: 91
                },
                easing : 'easeInQuart',
                duration : 800,
                direction : 'vertical'
            },
            after : {
                transition : {
                    rotateX: 180
                },
                easing : 'easeOutQuart',
                duration : 800,
                direction : 'vertical'
            }
        },

        {
            name : 'Spinning tiles to right (180&#176;)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            animation : {
                transition : {
                    rotateY: 180
                },
                easing : 'easeInOutQuart',
                duration : 1000,
                direction : 'horizontal'
            }
        },

        {
            name : 'Spinning tiles to left (180&#176;)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 75,
                sequence : 'reverse'
            },
            animation : {
                transition : {
                    rotateY: -180
                },
                easing : 'easeInOutQuart',
                duration : 1000,
                direction : 'horizontal'
            }
        },

        {
            name : 'Spinning tiles to bottom (180&#176;)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 75,
                sequence : 'col-forward'
            },
            animation : {
                transition : {
                    rotateX: -180
                },
                easing : 'easeInOutQuart',
                duration : 1000,
                direction : 'vertical'
            }
        },

        {
            name : 'Spinning tiles to top (180&#176;)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 75,
                sequence : 'col-reverse'
            },
            animation : {
                transition : {
                    rotateX: 180
                },
                easing : 'easeInOutQuart',
                duration : 1000,
                direction : 'vertical'
            }
        },

        {
            name : 'Horizontal spinning tiles random (180&#176;)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 75,
                sequence : 'random'
            },
            animation : {
                transition : {
                    rotateY: 180
                },
                easing : 'easeInOutQuart',
                duration : 1300,
                direction : 'horizontal'
            }
        },

        {
            name : 'Vertical spinning tiles random (180&#176;)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 75,
                sequence : 'random'
            },
            animation : {
                transition : {
                    rotateX: 180
                },
                easing : 'easeInOutQuart',
                duration : 1300,
                direction : 'vertical'
            }
        },

        {
            name : 'Scaling and spinning tiles to right (180&#176;)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            before : {
                transition : {
                    scale3d : .95
                },
                duration : 450,
                easing : 'easeInOutQuint'
            },
            animation : {
                transition : {
                    rotateY: 180
                },
                easing : 'easeInOutBack',
                duration : 1000,
                direction : 'horizontal'
            },
            after : {
                duration : 350,
                easing : 'easeInOutBack'
            }
        },

        {
            name : 'Scaling and spinning tiles to left (180&#176;)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 75,
                sequence : 'reverse'
            },
            before : {
                transition : {
                    scale3d : .95
                },
                duration : 450,
                easing : 'easeInOutQuint'
            },
            animation : {
                transition : {
                    rotateY: -180
                },
                easing : 'easeInOutBack',
                duration : 1000,
                direction : 'horizontal'
            },
            after : {
                duration : 350,
                easing : 'easeInOutBack'
            }
        },

        {
            name : 'Scaling and spinning tiles to bottom (180&#176;)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 75,
                sequence : 'col-forward'
            },
            before : {
                transition : {
                    scale3d : .95
                },
                duration : 450,
                easing : 'easeInOutQuint'
            },
            animation : {
                transition : {
                    rotateX: -180
                },
                easing : 'easeInOutBack',
                duration : 1000,
                direction : 'vertical'
            },
            after : {
                duration : 350,
                easing : 'easeInOutBack'
            }
        },

        {
            name : 'Scaling and spinning tiles to top (180&#176;)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 75,
                sequence : 'col-reverse'
            },
            before : {
                transition : {
                    scale3d : .95
                },
                duration : 450,
                easing : 'easeInOutQuint'
            },
            animation : {
                transition : {
                    rotateX: 180
                },
                easing : 'easeInOutBack',
                duration : 1000,
                direction : 'vertical'
            },
            after : {
                duration : 350,
                easing : 'easeInOutBack'
            }
        },

        {
            name : 'Scaling and horizontal spinning tiles random (180&#176;)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 75,
                sequence : 'random'
            },
            before : {
                transition : {
                    scale3d : .95, rotateX : 30
                },
                duration : 450,
                easing : 'easeInOutQuint'
            },
            animation : {
                transition : {
                    rotateY: 180, rotateX: -30
                },
                easing : 'easeInOutBack',
                duration : 1300,
                direction : 'horizontal'
            },
            after : {
                transition : {
                    rotateX : 0
                },
                duration : 350,
                easing : 'easeInOutBack'
            }
        },

        {
            name : 'Scaling and vertical spinning tiles random (180&#176;)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 75,
                sequence : 'random'
            },
            before : {
                transition : {
                    scale3d : .95, rotateY : -15
                },
                duration : 450,
                easing : 'easeInOutQuint'
            },
            animation : {
                transition : {
                    rotateX: 180, rotateY : 15
                },
                easing : 'easeInOutBack',
                duration : 1300,
                direction : 'vertical'
            },
            after : {
                transition : {
                    rotateY : 0
                },
                duration : 350,
                easing : 'easeInOutBack'
            }
        },

        {
            name : 'Spinning rows to right (180&#176;)',
            rows : [5,9],
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            animation : {
                transition : {
                    rotateY : 180
                },
                easing : 'easeInOutQuart',
                duration : 1500,
                direction : 'horizontal'
            }
        },

        {
            name : 'Spinning rows to left (180&#176;)',
            rows : [5,9],
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            animation : {
                transition : {
                    rotateY : -180
                },
                easing : 'easeInOutQuart',
                duration : 1500,
                direction : 'horizontal'
            }
        },

        {
            name : 'Spinning rows to bottom (180&#176;)',
            rows : [5,9],
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            animation : {
                transition : {
                    rotateX : -180
                },
                easing : 'easeInOutQuart',
                duration : 1000,
                direction : 'vertical'
            }
        },

        {
            name : 'Spinning rows to top (180&#176;)',
            rows : [5,9],
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'reverse'
            },
            animation : {
                transition : {
                    rotateX : 180
                },
                easing : 'easeInOutQuart',
                duration : 1000,
                direction : 'vertical'
            }
        },

        {
            name : 'Horizontal spinning rows random (180&#176;)',
            rows : [5,9],
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'random'
            },
            animation : {
                transition : {
                    rotateY : 180
                },
                easing : 'easeInOutQuart',
                duration : 1500,
                direction : 'horizontal'
            }
        },

        {
            name : 'Vertical spinning rows random (180&#176;)',
            rows : [5,9],
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'random'
            },
            animation : {
                transition : {
                    rotateX : -180
                },
                easing : 'easeInOutQuart',
                duration : 1500,
                direction : 'vertical'
            }
        },

        {
            name : 'Vertical spinning rows random (540&#176;)',
            rows : [3,7],
            cols : 1,
            tile : {
                delay : 150,
                sequence : 'random'
            },
            animation : {
                transition : {
                    rotateX : -540
                },
                easing : 'easeInOutQuart',
                duration : 2000,
                direction : 'vertical'
            }
        },

        {
            name : 'Scaling and spinning rows to right (180&#176;)',
            rows : [5,9],
            cols : 1,
            tile : {
                delay : 55,
                sequence : 'forward'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateY : 180
                },
                easing : 'easeInOutBack',
                duration : 1200,
                direction : 'horizontal'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutBack',
                duration : 600
            }
        },

        {
            name : 'Scaling and spinning rows to left (180&#176;)',
            rows : [5,9],
            cols : 1,
            tile : {
                delay : 55,
                sequence : 'reverse'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateY : -180
                },
                easing : 'easeInOutBack',
                duration : 1200,
                direction : 'horizontal'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutBack',
                duration : 600
            }
        },

        {
            name : 'Scaling and spinning rows to bottom (180&#176;)',
            rows : [5,9],
            cols : 1,
            tile : {
                delay : 55,
                sequence : 'forward'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateX : -180
                },
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'vertical'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutBack',
                duration : 600
            }
        },

        {
            name : 'Scaling and spinning rows to top (180&#176;)',
            rows : [5,9],
            cols : 1,
            tile : {
                delay : 55,
                sequence : 'reverse'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateX : 180
                },
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'vertical'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutBack',
                duration : 600
            }
        },

        {
            name : 'Scaling and horizontal spinning rows random (180&#176;)',
            rows : [5,9],
            cols : 1,
            tile : {
                delay : 55,
                sequence : 'random'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateY : 180
                },
                easing : 'easeInOutBack',
                duration : 1200,
                direction : 'horizontal'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutBack',
                duration : 600
            }
        },

        {
            name : 'Scaling and vertical spinning rows random (180&#176;)',
            rows : [5,9],
            cols : 1,
            tile : {
                delay : 55,
                sequence : 'random'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateX : -180
                },
                easing : 'easeInOutBack',
                duration : 600,
                direction : 'vertical'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutBack',
                duration : 600
            }
        },

        {
            name : 'Spinning columns to right (180&#176;)',
            rows : 1,
            cols : [5,9],
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            animation : {
                transition : {
                    rotateY : 180
                },
                easing : 'easeInOutQuart',
                duration : 1500,
                direction : 'horizontal'
            }
        },

        {
            name : 'Spinning columns to left (180&#176;)',
            rows : 1,
            cols : [5,9],
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            animation : {
                transition : {
                    rotateY : -180
                },
                easing : 'easeInOutQuart',
                duration : 1500,
                direction : 'horizontal'
            }
        },

        {
            name : 'Spinning columns to bottom (180&#176;)',
            rows : 1,
            cols : [5,9],
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            animation : {
                transition : {
                    rotateX : -180
                },
                easing : 'easeInOutQuart',
                duration : 1000,
                direction : 'vertical'
            }
        },

        {
            name : 'Spinning columns to top (180&#176;)',
            rows : 1,
            cols : [5,9],
            tile : {
                delay : 75,
                sequence : 'reverse'
            },
            animation : {
                transition : {
                    rotateX : 180
                },
                easing : 'easeInOutQuart',
                duration : 1000,
                direction : 'vertical'
            }
        },

        {
            name : 'Horizontal spinning columns random (180&#176;)',
            rows : 1,
            cols : [5,9],
            tile : {
                delay : 75,
                sequence : 'random'
            },
            animation : {
                transition : {
                    rotateY : 180
                },
                easing : 'easeInOutQuart',
                duration : 1500,
                direction : 'horizontal'
            }
        },

        {
            name : 'Vertical spinning columns random (180&#176;)',
            rows : 1,
            cols : [5,9],
            tile : {
                delay : 75,
                sequence : 'random'
            },
            animation : {
                transition : {
                    rotateX : -180
                },
                easing : 'easeInOutQuart',
                duration : 1500,
                direction : 'vertical'
            }
        },

        {
            name : 'Horizontal spinning columns random (540&#176;)',
            rows : 1,
            cols : [4,9],
            tile : {
                delay : 150,
                sequence : 'random'
            },
            animation : {
                transition : {
                    rotateY : 540
                },
                easing : 'easeInOutQuart',
                duration : 2000,
                direction : 'horizontal'
            }
        },

        {
            name : 'Scaling and spinning columns to right (180&#176;)',
            rows : 1,
            cols : [7,11],
            tile : {
                delay : 55,
                sequence : 'forward'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateY : 180
                },
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'horizontal'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutBack',
                duration : 600
            }
        },

        {
            name : 'Scaling and spinning columns to left (180&#176;)',
            rows : 1,
            cols : [7,11],
            tile : {
                delay : 55,
                sequence : 'reverse'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateY : -180
                },
                easing : 'easeInOutQuart',
                duration : 600,
                direction : 'horizontal'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutBack',
                duration : 600
            }
        },

        {
            name : 'Scaling and spinning columns to bottom (180&#176;)',
            rows : 1,
            cols : [7,11],
            tile : {
                delay : 55,
                sequence : 'forward'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateX : -180
                },
                easing : 'easeInOutBack',
                duration : 1200,
                direction : 'vertical'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutBack',
                duration : 600
            }
        },

        {
            name : 'Scaling and spinning columns to top (180&#176;)',
            rows : 1,
            cols : [7,11],
            tile : {
                delay : 75,
                sequence : 'reverse'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateX : 180
                },
                easing : 'easeInOutBack',
                duration : 1200,
                direction : 'vertical'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutBack',
                duration : 600
            }
        },

        {
            name : 'Scaling and horizontal spinning columns random (180&#176;)',
            rows : 1,
            cols : [7,11],
            tile : {
                delay : 75,
                sequence : 'random'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateY : 180
                },
                easing : 'easeInOutBack',
                duration : 600,
                direction : 'horizontal'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutBack',
                duration : 600
            }
        },

        {
            name : 'Scaling and vertical spinning columns random (180&#176;)',
            rows : 1,
            cols : [7,11],
            tile : {
                delay : 75,
                sequence : 'random'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateX : -180
                },
                easing : 'easeInOutBack',
                duration : 1200,
                direction : 'vertical'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutBack',
                duration : 600
            }
        },

        {
            name : 'Drunk colums scaling and spinning to right (180&#176;)',
            rows : 1,
            cols : [7,11],
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            before : {
                transition : {
                    scale3d : .85, rotateX : -30
                },
                duration : 600,
                easing : 'easeOutQuart'
            },
            animation : {
                transition : {
                    rotateX : -30, rotateY : 180
                },
                easing : 'easeInOutQuart',
                duration : 1000,
                direction : 'horizontal'
            },
            after : {
                transition : {
                    rotateX : 0, delay : 200
                },
                easing : 'easeOutQuart',
                duration : 600
            }
        },

        {
            name : 'Drunk colums scaling and spinning to left (180&#176;)',
            rows : 1,
            cols : [7,11],
            tile : {
                delay : 75,
                sequence : 'reverse'
            },
            before : {
                transition : {
                    scale3d : .85, rotateX : -30
                },
                duration : 600,
                easing : 'easeOutQuart'
            },
            animation : {
                transition : {
                    rotateX : 30, rotateY : -180
                },
                easing : 'easeInOutQuart',
                duration : 1000,
                direction : 'horizontal'
            },
            after : {
                transition : {
                    rotateX : 0, delay : 200
                },
                easing : 'easeOutQuart',
                duration : 600
            }
        },

        // Turning transitions (90deg, large depth);

        {
            name : 'Turning cuboid to right (90&#176;)',
            rows : 1,
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            animation : {
                transition : {
                    rotateY: 90
                },
                easing : 'easeInOutQuart',
                duration : 1500,
                direction : 'horizontal'
            }
        },

        {
            name : 'Turning cuboid to left (90&#176;)',
            rows : 1,
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            animation : {
                transition : {
                    rotateY: -90
                },
                easing : 'easeInOutQuart',
                duration : 1500,
                direction : 'horizontal'
            }
        },

        {
            name : 'Turning cuboid to bottom (90&#176;)',
            rows : 1,
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            animation : {
                transition : {
                    rotateX: -90
                },
                easing : 'easeInOutQuart',
                duration : 1500,
                direction : 'vertical'
            }
        },

        {
            name : 'Turning cuboid to top (90&#176;)',
            rows : 1,
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            animation : {
                transition : {
                    rotateX: 90
                },
                easing : 'easeInOutQuart',
                duration : 1500,
                direction : 'vertical'
            }
        },

        {
            name : 'Scaling and turning cuboid to right (90&#176;)',
            rows : 1,
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'random'
            },
            animation : {
                transition : {
                    scale3d : .8, rotate: 7, rotateX: 10, rotateY: 45
                },
                easing : 'easeInOutQuad',
                duration : 800,
                direction : 'horizontal'
            },
            after : {
                transition : {
                    rotate : 0, rotateX: 0, rotateY : 90
                },
                duration : 800,
                easing : 'easeInOutQuad'
            }
        },

        {
            name : 'Scaling and turning cuboid to left (90&#176;)',
            rows : 1,
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'random'
            },
            animation : {
                transition : {
                    scale3d : .8, rotate: -7, rotateX : 10, rotateY: -45
                },
                easing : 'easeInOutQuad',
                duration : 800,
                direction : 'horizontal'
            },
            after : {
                transition : {
                    rotate : 0, rotateX : 0, rotateY : -90
                },
                duration : 800,
                easing : 'easeInOutQuad'
            }
        },

        {
            name : 'Scaling and turning cuboids to right (90&#176;)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 450,
                easing : 'easeInOutQuint'
            },
            animation : {
                transition : {
                    rotateY: 90
                },
                easing : 'easeInOutBack',
                duration : 1000,
                direction : 'horizontal'
            },
            after : {
                duration : 350,
                easing : 'easeInOutBack'
            }
        },

        {
            name : 'Scaling and turning cuboids to left (90&#176;)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 75,
                sequence : 'reverse'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 450,
                easing : 'easeInOutQuint'
            },
            animation : {
                transition : {
                    rotateY: -90
                },
                easing : 'easeInOutBack',
                duration : 1000,
                direction : 'horizontal'
            },
            after : {
                duration : 350,
                easing : 'easeInOutBack'
            }
        },

        {
            name : 'Scaling and turning cuboids to bottom (90&#176;)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 75,
                sequence : 'col-forward'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 450,
                easing : 'easeInOutQuint'
            },
            animation : {
                transition : {
                    rotateX: -90
                },
                easing : 'easeInOutBack',
                duration : 1000,
                direction : 'vertical'
            },
            after : {
                duration : 350,
                easing : 'easeInOutBack'
            }
        },

        {
            name : 'Scaling and turning cuboids to top (90&#176;)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 75,
                sequence : 'col-reverse'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 450,
                easing : 'easeInOutQuint'
            },
            animation : {
                transition : {
                    rotateX: 90
                },
                easing : 'easeInOutBack',
                duration : 1000,
                direction : 'vertical'
            },
            after : {
                duration : 350,
                easing : 'easeInOutBack'
            }
        },

        {
            name : 'Scaling and horizontal turning cuboids random (90&#176;)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 75,
                sequence : 'random'
            },
            before : {
                transition : {
                    scale3d : .65, rotateX : -15
                },
                duration : 700,
                easing : 'easeInOutQuint'
            },
            animation : {
                transition : {
                    rotateY : 75, rotateX : 15
                },
                easing : 'easeInOutBack',
                duration : 700,
                direction : 'horizontal'
            },
            after : {
                transition : {
                    rotateY : 90, rotateX : 0
                },
                duration : 700,
                easing : 'easeInOutBack'
            }
        },

        {
            name : 'Scaling and vertical turning cuboids random (90&#176;)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 75,
                sequence : 'random'
            },
            before : {
                transition : {
                    scale3d : .65, rotateY : 15
                },
                duration : 700,
                easing : 'easeInOutQuint'
            },
            animation : {
                transition : {
                    rotateX: 75, rotateY : -15
                },
                easing : 'easeInOutBack',
                duration : 700,
                direction : 'vertical'
            },
            after : {
                transition : {
                    rotateX: 90, rotateY : 0
                },
                duration : 700,
                easing : 'easeInOutBack'
            }
        },

        {
            name : 'Turning rows to right (90&#176;)',
            rows : [5,9],
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            animation : {
                transition : {
                    rotateY : 90
                },
                easing : 'easeInOutQuart',
                duration : 1500,
                direction : 'horizontal'
            }
        },

        {
            name : 'Turning rows to left (90&#176;)',
            rows : [5,9],
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            animation : {
                transition : {
                    rotateY : -90
                },
                easing : 'easeInOutQuart',
                duration : 1500,
                direction : 'horizontal'
            }
        },

        {
            name : 'Horizontal turning rows random (90&#176;)',
            rows : [5,9],
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'random'
            },
            animation : {
                transition : {
                    rotateY : 90
                },
                easing : 'easeInOutQuart',
                duration : 1500,
                direction : 'horizontal'
            }
        },

        {
            name : 'Scaling and turning rows to right (90&#176;)',
            rows : [5,9],
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            before : {
                transition : {
                    scale3d : .85, rotateX : 3
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateY : 87, rotateX : 0
                },
                easing : 'easeInOutBack',
                duration : 1000,
                direction : 'horizontal'
            },
            after : {
                transition : {
                    delay : 200, rotateY : 90
                },
                easing : 'easeOutBack',
                duration : 600
            }
        },

        {
            name : 'Scaling and turning rows to left (90&#176;)',
            rows : [5,9],
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'reverse'
            },
            before : {
                transition : {
                    scale3d : .85, rotateX : 3
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateY : -90, rotateX : 0
                },
                easing : 'easeInOutBack',
                duration : 1000,
                direction : 'horizontal'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutBack',
                duration : 600
            }
        },

        {
            name : 'Scaling and turning rows to bottom (90&#176;)',
            rows : [5,9],
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateX : -90
                },
                easing : 'easeInOutBack',
                duration : 1000,
                direction : 'vertical'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutBack',
                duration : 600
            }
        },

        {
            name : 'Scaling and turning rows to top (90&#176;)',
            rows : [5,9],
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'reverse'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateX : 90
                },
                easing : 'easeInOutBack',
                duration : 1000,
                direction : 'vertical'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutBack',
                duration : 600
            }
        },

        {
            name : 'Scaling and horizontal turning rows random (90&#176;)',
            rows : [5,9],
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'random'
            },
            before : {
                transition : {
                    scale3d : .85, rotateX : 3
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateY : 90, rotateX : 0
                },
                easing : 'easeInOutBack',
                duration : 1000,
                direction : 'horizontal'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutBack',
                duration : 600
            }
        },

        {
            name : 'Scaling and vertical turning rows random (90&#176;)',
            rows : [5,9],
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'random'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateX : -90
                },
                easing : 'easeInOutBack',
                duration : 1000,
                direction : 'vertical'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutBack',
                duration : 600
            }
        },

        {
            name : 'Scaling and horizontal turning drunk rows to right (90&#176;)',
            rows : [7,11],
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            animation : {
                transition : {
                    scale3d : .85, rotateX : 5, rotateY : 45
                },
                easing : 'easeInOutQuint',
                duration : 1000,
                direction : 'horizontal'
            },
            after : {
                transition : {
                    rotateX : 0, rotateY : 90
                },
                easing : 'easeInOutQuint',
                duration : 1000
            }
        },

        {
            name : 'Scaling and horizontal turning drunk rows to left (90&#176;)',
            rows : [7,11],
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'reverse'
            },
            animation : {
                transition : {
                    scale3d : .85, rotateX : 5, rotateY : -45
                },
                easing : 'easeInOutQuint',
                duration : 1000,
                direction : 'horizontal'
            },
            after : {
                transition : {
                    rotateX : 0, rotateY : -90
                },
                easing : 'easeInOutQuint',
                duration : 1000
            }
        },

        {
            name : 'Turning columns to bottom (90&#176;)',
            rows : 1,
            cols : [5,9],
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            animation : {
                transition : {
                    rotateX : -90
                },
                easing : 'easeInOutQuart',
                duration : 1000,
                direction : 'vertical'
            }
        },

        {
            name : 'Turning columns to top (90&#176;)',
            rows : 1,
            cols : [5,9],
            tile : {
                delay : 75,
                sequence : 'reverse'
            },
            animation : {
                transition : {
                    rotateX : 90
                },
                easing : 'easeInOutQuart',
                duration : 1000,
                direction : 'vertical'
            }
        },

        {
            name : 'Vertical turning columns random (90&#176;)',
            rows : 1,
            cols : [5,9],
            tile : {
                delay : 75,
                sequence : 'random'
            },
            animation : {
                transition : {
                    rotateX : -90
                },
                easing : 'easeInOutQuart',
                duration : 1000,
                direction : 'vertical'
            }
        },

        {
            name : 'Scaling and turning columns to bottom (90&#176;)',
            rows : 1,
            cols : [7,11],
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateX : -90
                },
                easing : 'easeInOutBack',
                duration : 1000,
                direction : 'vertical'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutBack',
                duration : 600
            }
        },

        {
            name : 'Scaling and turning columns to top (90&#176;)',
            rows : 1,
            cols : [7,11],
            tile : {
                delay : 75,
                sequence : 'reverse'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateX : 90
                },
                easing : 'easeInOutBack',
                duration : 1000,
                direction : 'vertical'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutBack',
                duration : 600
            }
        },

        {
            name : 'Scaling and turning columns to right (90&#176;)',
            rows : 1,
            cols : [7,11],
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateY : 90
                },
                easing : 'easeInOutBack',
                duration : 1000,
                direction : 'horizontal'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutBack',
                duration : 600
            }
        },

        {
            name : 'Scaling and turning columns to left (90&#176;)',
            rows : 1,
            cols : [7,11],
            tile : {
                delay : 75,
                sequence : 'reverse'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateY : -90
                },
                easing : 'easeInOutBack',
                duration : 1000,
                direction : 'horizontal'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutBack',
                duration : 600
            }
        },

        {
            name : 'Scaling and horizontal turning columns random (90&#176;)',
            rows : 1,
            cols : [7,11],
            tile : {
                delay : 75,
                sequence : 'random'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateY : 90
                },
                easing : 'easeInOutBack',
                duration : 1000,
                direction : 'horizontal'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutBack',
                duration : 600
            }
        },

        {
            name : 'Scaling and vertical turning columns random (90&#176;)',
            rows : 1,
            cols : [7,11],
            tile : {
                delay : 75,
                sequence : 'random'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateX : -90
                },
                easing : 'easeInOutBack',
                duration : 1000,
                direction : 'vertical'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutBack',
                duration : 600
            }
        },

        {
            name : 'Scaling and vertical turning drunk columns to right (90&#176;)',
            rows : 1,
            cols : [7,11],
            tile : {
                delay : 75,
                sequence : 'forward'
            },
            animation : {
                transition : {
                    scale3d : .85, rotateX : 45, rotateY : -5
                },
                easing : 'easeInOutQuint',
                duration : 1000,
                direction : 'vertical'
            },
            after : {
                transition : {
                    rotateX : 90, rotateY : 0
                },
                easing : 'easeInOutQuint',
                duration : 1000
            }
        },

        {
            name : 'Scaling and vertical turning drunk columns to left (90&#176;)',
            rows : 1,
            cols : [7,11],
            tile : {
                delay : 75,
                sequence : 'reverse'
            },
            animation : {
                transition : {
                    scale3d : .85, rotateX : -45, rotateY : -5
                },
                easing : 'easeInOutQuint',
                duration : 1000,
                direction : 'vertical'
            },
            after : {
                transition : {
                    rotateX : -90, rotateY : 0
                },
                easing : 'easeInOutQuint',
                duration : 1000
            }
        },

        // Spinning transitions (180deg, large detph)

        {
            name : 'Spinning cuboid to right (180&#176;, large depth)',
            rows : 1,
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'forward',
                depth : 'large'
            },
            animation : {
                transition : {
                    rotateY: 180
                },
                easing : 'easeInOutQuart',
                duration : 1500,
                direction : 'horizontal'
            }
        },

        {
            name : 'Spinning cuboid to left (180&#176;, large depth)',
            rows : 1,
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'forward',
                depth : 'large'
            },
            animation : {
                transition : {
                    rotateY: -180
                },
                easing : 'easeInOutQuart',
                duration : 1500,
                direction : 'horizontal'
            }
        },

        {
            name : 'Spinning cuboid to bottom (180&#176;, large depth)',
            rows : 1,
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'forward',
                depth : 'large'
            },
            animation : {
                transition : {
                    rotateX: -180
                },
                easing : 'easeInOutQuart',
                duration : 1500,
                direction : 'vertical'
            }
        },

        {
            name : 'Spinning cuboid to top (180&#176;, large depth)',
            rows : 1,
            cols : 1,
            tile : {
                delay : 75,
                sequence : 'forward',
                depth : 'large'
            },
            animation : {
                transition : {
                    rotateX: 180
                },
                easing : 'easeInOutQuart',
                duration : 1500,
                direction : 'vertical'
            }
        },

        {
            name : 'Scaling and spinning cuboids to right (180&#176;, large depth)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 75,
                sequence : 'forward',
                depth: 'large'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 450,
                easing : 'easeInOutQuint'
            },
            animation : {
                transition : {
                    rotateY: 180
                },
                easing : 'easeInOutBack',
                duration : 1000,
                direction : 'horizontal'
            },
            after : {
                duration : 350,
                easing : 'easeInOutBack'
            }
        },

        {
            name : 'Scaling and spinning cuboids to left (180&#176;, large depth)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 75,
                sequence : 'reverse',
                depth: 'large'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 450,
                easing : 'easeInOutQuint'
            },
            animation : {
                transition : {
                    rotateY: -180
                },
                easing : 'easeInOutBack',
                duration : 1000,
                direction : 'horizontal'
            },
            after : {
                duration : 350,
                easing : 'easeInOutBack'
            }
        },

        {
            name : 'Scaling and spinning cuboids to bottom (180&#176;, large depth)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 75,
                sequence : 'col-forward',
                depth: 'large'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 450,
                easing : 'easeInOutQuint'
            },
            animation : {
                transition : {
                    rotateX: -180
                },
                easing : 'easeInOutBack',
                duration : 1000,
                direction : 'vertical'
            },
            after : {
                duration : 350,
                easing : 'easeInOutBack'
            }
        },

        {
            name : 'Scaling and spinning cuboids to top (180&#176;, large depth)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 75,
                sequence : 'col-reverse',
                depth: 'large'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 450,
                easing : 'easeInOutQuint'
            },
            animation : {
                transition : {
                    rotateX: 180
                },
                easing : 'easeInOutBack',
                duration : 1000,
                direction : 'vertical'
            },
            after : {
                duration : 350,
                easing : 'easeInOutBack'
            }
        },

        {
            name : 'Scaling and horizontal spinning cuboids random (180&#176;, large depth)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 75,
                sequence : 'random',
                depth: 'large'
            },
            before : {
                transition : {
                    scale3d : .65
                },
                duration : 700,
                easing : 'easeInOutQuint'
            },
            animation : {
                transition : {
                    rotateY : 180
                },
                easing : 'easeInOutBack',
                duration : 700,
                direction : 'horizontal'
            },
            after : {
                duration : 700,
                easing : 'easeInOutBack'
            }
        },

        {
            name : 'Scaling and vertical spinning cuboids random (180&#176;, large depth)',
            rows : [2,4],
            cols : [4,7],
            tile : {
                delay : 75,
                sequence : 'random',
                depth: 'large'
            },
            before : {
                transition : {
                    scale3d : .65
                },
                duration : 700,
                easing : 'easeInOutQuint'
            },
            animation : {
                transition : {
                    rotateX: 180
                },
                easing : 'easeInOutBack',
                duration : 700,
                direction : 'vertical'
            },
            after : {
                duration : 700,
                easing : 'easeInOutBack'
            }
        },

        {
            name : 'Scaling and spinning rows to right (180&#176;, large depth)',
            rows : [5,9],
            cols : 1,
            tile : {
                delay : 65,
                sequence : 'forward',
                depth: 'large'
            },
            before : {
                transition : {
                    scale3d : .85, rotateX : 3
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateY : 180, rotateX : -3
                },
                easing : 'easeInOutQuart',
                duration : 1200,
                direction : 'horizontal'
            },
            after : {
                transition : {
                    delay : 200, rotateX : 0
                },
                easing : 'easeOutQuart',
                duration : 400
            }
        },

        {
            name : 'Scaling and spinning rows to left (180&#176;, large depth)',
            rows : [5,9],
            cols : 1,
            tile : {
                delay : 65,
                sequence : 'reverse',
                depth: 'large'
            },
            before : {
                transition : {
                    scale3d : .85, rotateX : 3
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateY : -180, rotateX : -3
                },
                easing : 'easeInOutQuart',
                duration : 1200,
                direction : 'horizontal'
            },
            after : {
                transition : {
                    delay : 200, rotateX : 0
                },
                easing : 'easeOutQuart',
                duration : 400
            }
        },

        {
            name : 'Scaling and spinning rows to bottom (180&#176;, large depth)',
            rows : [5,9],
            cols : 1,
            tile : {
                delay : 65,
                sequence : 'forward',
                depth: 'large'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateX : -180
                },
                easing : 'easeInOutBack',
                duration : 1000,
                direction : 'vertical'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutQuart',
                duration : 400
            }
        },

        {
            name : 'Scaling and spinning rows to top (180&#176;, large depth)',
            rows : [5,9],
            cols : 1,
            tile : {
                delay : 65,
                sequence : 'reverse',
                depth: 'large'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateX : 180
                },
                easing : 'easeInOutBack',
                duration : 1000,
                direction : 'vertical'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutQuart',
                duration : 400
            }
        },

        {
            name : 'Scaling and horizontal spinning rows random (180&#176;, large depth)',
            rows : [5,9],
            cols : 1,
            tile : {
                delay : 65,
                sequence : 'random',
                depth: 'large'
            },
            before : {
                transition : {
                    scale3d : .85, rotateX : 3
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateY : 180, rotateX : -3
                },
                easing : 'easeInOutQuart',
                duration : 1200,
                direction : 'horizontal'
            },
            after : {
                transition : {
                    delay : 200, rotateX : 0
                },
                easing : 'easeOutQuart',
                duration : 400
            }
        },

        {
            name : 'Scaling and vertical spinning rows random (180&#176;, large depth)',
            rows : [5,9],
            cols : 1,
            tile : {
                delay : 65,
                sequence : 'random',
                depth: 'large'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateX : -180
                },
                easing : 'easeInOutBack',
                duration : 1000,
                direction : 'vertical'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutQuart',
                duration : 400
            }
        },

        {
            name : 'Scaling and spinning columns to bottom (180&#176;, large depth)',
            rows : 1,
            cols : [7,11],
            tile : {
                delay : 65,
                sequence : 'forward',
                depth: 'large'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateX : -180
                },
                easing : 'easeInOutQuart',
                duration : 1200,
                direction : 'vertical'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutQuart',
                duration : 400
            }
        },

        {
            name : 'Scaling and spinning columns to top (180&#176;, large depth)',
            rows : 1,
            cols : [7,11],
            tile : {
                delay : 65,
                sequence : 'reverse',
                depth: 'large'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateX : 180
                },
                easing : 'easeInOutQuart',
                duration : 1200,
                direction : 'vertical'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutQuart',
                duration : 400
            }
        },

        {
            name : 'Scaling and spinning columns to right (180&#176;, large depth)',
            rows : 1,
            cols : [7,11],
            tile : {
                delay : 65,
                sequence : 'forward',
                depth: 'large'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateY : 180
                },
                easing : 'easeInOutBack',
                duration : 1000,
                direction : 'horizontal'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutQuart',
                duration : 400
            }
        },

        {
            name : 'Scaling and spinning columns to left (180&#176;, large depth)',
            rows : 1,
            cols : [7,11],
            tile : {
                delay : 65,
                sequence : 'reverse',
                depth: 'large'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateY : -180
                },
                easing : 'easeInOutBack',
                duration : 1000,
                direction : 'horizontal'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutQuart',
                duration : 400
            }
        },

        {
            name : 'Scaling and horizontal spinning columns random (180&#176;, large depth)',
            rows : 1,
            cols : [7,11],
            tile : {
                delay : 65,
                sequence : 'random',
                depth: 'large'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateY : 180
                },
                easing : 'easeInOutBack',
                duration : 1000,
                direction : 'horizontal'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutQuart',
                duration : 400
            }
        },

        {
            name : 'Scaling and vertical spinning columns random (180&#176;, large depth)',
            rows : 1,
            cols : [7,11],
            tile : {
                delay : 65,
                sequence : 'random',
                depth: 'large'
            },
            before : {
                transition : {
                    scale3d : .85
                },
                duration : 600,
                easing : 'easeOutBack'
            },
            animation : {
                transition : {
                    rotateX : -180
                },
                easing : 'easeInOutQuart',
                duration : 1200,
                direction : 'vertical'
            },
            after : {
                transition : {
                    delay : 200
                },
                easing : 'easeOutQuart',
                duration : 400
            }
        }
    ]
};
