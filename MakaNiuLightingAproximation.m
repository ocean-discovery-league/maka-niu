%% FEEL FREE TO EDIT
%Adjustable Parameters for Geometry of the Modules

theta_deg = 62.2    %Theta is the camera lens angle 
alpha_deg = 25  %Alpha is the angle of light 
zeta_deg = 20   %Zeta is the angle of the position of the light from the verticle or 90 degree
x_dist = .3     %x_dist is the distance between the camera and the light horixantaly 
obj_y = 2   %the distance from the camera to object 

%set ideal range for camera/ lighting
range_close = .5    %in meters
range_far = 5   %in meters

%% FEEL FREE TO EDIT
%Given Variables (can be adjusted based on conditions) 
kd = .8;    %light attenuation coefficent 
emiss = .12;    %irradience of the object
pix_area = 1.2544e-12;  %pixel area (1.12)^2 
efficiency = 200;   %lm/watts
QE = .4;    %Quantum Efficency
FPS = 40    %Frames per second 

min_photons_per_sensor = 30 
max_photons_per_sensor = 30*400 %really 1/3 max 

%% ADJUSTING INPUT VARIABLES TO RADIANS
%convert all degrees to radians 
theta = theta_deg*pi/180;
alpha = alpha_deg*pi/180;
zeta = zeta_deg*pi/180;

%% SHOW GRAPHICALLY 
%To solve for the Intersection Points of the symetrical light beams 
LP_y =  x_dist*tan((1.5708-zeta) - (alpha/2));
   %the LP is the y value point closet to the camera where the beams intersect
HP_y = x_dist*tan((1.5708-zeta) + (alpha/2));
    %the LP is the y value point closet to the camera where the beams intersect
    %1.5708 is 90 degrees to offset 

%show camera angle
plot(0,0, 'r*')

line([0,(-10*tan(theta/2))], [0,10], 'Color', 'r', 'LineWidth', 3)
line([0,(10*tan(theta/2))], [0,10], 'Color', 'r', 'LineWidth', 3)
grid on
%plot the lights
hold on
plot(-(x_dist),0, 'b*')
hold on
plot((x_dist),0, 'b*')
hold on 
xlim([-5 5])
ylim([0 8])
% define light angles
line([-(x_dist),((10*tan(zeta))-(x_dist))], [0,10], 'Color', 'k', 'LineWidth', 1, 'LineStyle',':')
line([(x_dist),((-10*tan(zeta))-(x_dist))], [0,10], 'Color', 'k', 'LineWidth', 1, 'LineStyle',':')

%define left light beam 
line([-(x_dist),(10*tan(zeta+alpha/2))-(x_dist)], [0,10], 'Color', 'b', 'LineWidth', 2);
line([-(x_dist),(10*tan(zeta-alpha/2))-(x_dist)], [0,10], 'Color', 'b', 'LineWidth', 2);

% %define right light beam
line([(x_dist),(-10*tan(zeta+alpha/2))+(x_dist)], [0,10], 'Color', 'b', 'LineWidth', 2);
line([(x_dist),(-10*tan(zeta-alpha/2))+(x_dist)], [0,10], 'Color', 'b', 'LineWidth', 2);

%Fill in with light
%Fill in the Left Beam 
LB_X = [-(x_dist),(10*tan(zeta+alpha/2))-(x_dist) ,(10*tan(zeta-alpha/2))-(x_dist) ];
LB_Y = [0, 10,10];
patch(LB_X, LB_Y, 'Y','FaceAlpha',.2);

%Fill in the right Beam
RB_X = [(x_dist),(-10*tan(zeta+alpha/2))+(x_dist) ,(-10*tan(zeta-alpha/2))+(x_dist) ];
RB_Y = [0, 10,10];
patch(RB_X, RB_Y, 'Y','FaceAlpha',.2);

%fill in the camera Lense angle
CL_X = [0 , (-10*tan(theta/2)), (10*tan(theta/2))];
CL_Y = [0, 10 ,10] ;
%patch(CL_X, CL_Y, 'g','FaceAlpha',.01)

%mark the ideal range
%line([-5,5], [range_close, range_close], 'Color', 'k', 'LineWidth', 1);
%line([-5,5], [range_far, range_far], 'Color', 'k', 'LineWidth', 1);
hold on 

txt = {'distance' x_dist, 'Angle of light' zeta_deg ,'Light aperature' alpha_deg};
text(3,2,txt,'FontSize', 18)

improvePlot()
ylabel('[m]')
xlabel('[m]' )

%% CALCULATIONS FOR LIGHT 
%calculate distance to object from the light source 
light_distance = sqrt((x_dist^2)+(obj_y)^2);

%caclulate solid angle 
solid_angle = 2*pi*(1-cos(alpha/2));
%calculate surface area for distance and angle given 
surf_area = solid_angle * (light_distance)^2;

%calculate energy per photon 
h = 6.626*10^-34;   %planks Constant [J*s]
c = 2.998*10^8;     %speed of light [m/s]
lamda = 480*10^-9;  %blue wavelength [m]
energy_per_photon = h*c/(lamda);    %average energy per photon using blue light =[J]

%% Calculation for Minimum Light 
%FINDING THE MINIMUM LUMEN SO WE REACH ABSOLUTE THRESHOLD

min_photons_per_pix = (min_photons_per_sensor*FPS)/QE; %neccesary photons per pixel area per second - quantum efficiency and FPS

min_watts_per_pix = min_photons_per_pix*energy_per_photon; %watts per pixel using the energy per photon and the minimum phtons

min_lumens_per_pix = min_watts_per_pix*efficiency; %LED efficiency to conver watts to Lumens 

min_lux_to_cam = min_lumens_per_pix/pix_area; %Pixel area to conver lumens to Lux

min_lux_reflected = min_lux_to_cam/(exp(-kd*obj_y)); %Accounting for the attenuation of light from the object to camera

min_lux_at_object = min_lux_reflected/emiss; %Accounting for the irradiance of the object

min_lux_to_object = min_lux_at_object/(exp(-kd*light_distance)); %accounting for the attenuation 

min_lumen = min_lux_to_object*surf_area %calculating the area of illumination for the LED, and thus the Lumens at the orgin

%% Calculations for 1/3 light 

max_photons_per_pix = (max_photons_per_sensor*FPS)/QE;

max_watts_per_pix = max_photons_per_pix*energy_per_photon;

max_lumens_per_pix = max_watts_per_pix*efficiency;

max_lux_to_cam = max_lumens_per_pix/pix_area;

max_lux_reflected = max_lux_to_cam/(exp(-kd*obj_y));

max_lux_at_object = max_lux_reflected/emiss;

max_lux_to_object = max_lux_at_object/(exp(-kd*light_distance));

max_lumen = max_lux_to_object*surf_area

%%
%improve plot function for nice graph
function [] = improvePlot()
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    % Plot parameters
    % MATLAB treats mac and PC displays differently which can create
    % weird looking graphs. Here we handle system differences

    if ismac
        plot_width_in_px = 800;
        plot_height_in_px = 800;
        marker_size=15;
        marker_line_width=2.5;
        box_thickness = 3;
        axis_tick_font_size = 24;
        axis_label_font_size = 24;
        legend_font_size = 20;
        error_bar_cap_size = 15;
    else % (ispc || isunix)
        plot_width_in_px = 600;
        plot_height_in_px = 600;
        marker_size=10;
        marker_line_width=2.0;
        box_thickness = 2;
        axis_tick_font_size = 18;
        axis_label_font_size = 18;
        legend_font_size = 16;
        error_bar_cap_size = 10;
    end
    
    marker_outline = 'matching'; % could be 'black' or 'matching'

    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

    % Use h as handle for current figure
    hFig = gcf;                    
    % Change figure background colour to white
    set(hFig, 'Color', 'white');

    % Make the figure bigger
    set(hFig, 'rend', 'painters', 'Units', 'pixels', 'pos', ...
        [100 100 plot_width_in_px plot_height_in_px]);

    % Grab the axes handle(s)
    axis_handles=findobj(hFig,'type','axe');

    % Iterate over all axes handle(s), this is useful if there are subplots
    for i = 1:length(axis_handles)
        ax = axis_handles(i);

        % Change default font size (tick labels, legend, etc.)
        set(ax, 'FontSize', axis_tick_font_size, 'FontName', 'Arial', 'LineWidth', box_thickness);
        
        set(ax, 'Box', 'on');

        % Change font size for axis text labels
        set(get(ax, 'XLabel'),'FontSize', axis_label_font_size, 'FontWeight', 'Bold');
        set(get(ax, 'YLabel'),'FontSize', axis_label_font_size, 'FontWeight', 'Bold');
        
        try % try statement to avoid error with categorical axes
        ax.XRuler.Exponent = 0; % Remove exponential notation from the X axis
        ax.YRuler.Exponent = 0; % Remove exponential notation from the Y axis
        catch
        end
        
    end
    
    % Find all the lines, and markers
    LineH = findobj(hFig, 'type', 'line', '-or', 'type', 'errorbar');

    if(~isempty(LineH))
        for i=1:length(LineH) % Iterate over all lines in the plot
            % Decide what color for the marker edges
            this_line_color = get(LineH(i),'color');
            if strcmp(marker_outline, 'black')
                marker_outline_color = 'black';
            elseif strcmp(marker_outline, 'matching')
                marker_outline_color = this_line_color;
            else
                marker_outline_color = 'black';
            end

            % If the LineWidth has not been customized, then change it
            if (get(LineH(i), 'LineWidth') <= 1.0)
                set(LineH(i), 'LineWidth', marker_line_width)
            end
            % Change lines and markers if they exist on the plot
            set(LineH(i),   'MarkerSize', marker_size, ...
                'MarkerEdgeColor', marker_outline_color, ...
                'MarkerFaceColor', this_line_color);
        end
    end

    % Find and change the error bars
    LineH = findobj(hFig, 'type', 'errorbar');
    if(~isempty(LineH))
        for i=1:length(LineH) % Iterate over all lines in the plot
            LineH(i).CapSize=error_bar_cap_size;
%             LineH(i).Color = [0 0 0]; % Set all error bars to black

        end
    end

    % Find the legend, and if there is one, change it  
    h = get(hFig,'children');
    for k = 1:length(h)
        if strcmpi(get(h(k),'Tag'),'legend')
            set(h(k), 'FontSize', legend_font_size, 'location', 'best');
            break;
        end
    end

end
