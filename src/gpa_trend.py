import matplotlib.pyplot as plt

def create_gpa_sparkline(min, q1, median, q3, max, x, path, width=3, height=1.5):
    
    # Choose size and background
    fig, ax = plt.subplots(figsize=(width, height))
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)

    # Set variables for graph
    stats = [{
        'label': '',  # Leave blank to avoid text on the y-axis
        'whislo': min,
        'q1': q1,
        'med': median,
        'q3': q3,
        'whishi': max
    }]

    # Styling
    box_color = '#D0E2FF'     
    line_color = '#789BE4'    
    
    boxprops = dict(facecolor=box_color, color=line_color, linewidth=1.5)
    whiskerprops = dict(color=line_color, linewidth=1.5)
    capprops = dict(color=line_color, linewidth=1.5)
    medianprops = dict(color=line_color, linewidth=1.5)

    # Draw the boxplot
    ax.bxp(stats, vert=False, patch_artist=True, showfliers=False,
           boxprops=boxprops, whiskerprops=whiskerprops, 
           capprops=capprops, medianprops=medianprops)

    # Use ranges in order to determine color
    if x < q1:
        dot_color = '#D62728'  
    elif x <= q3:
        dot_color = '#FF9800'  
    else:
        dot_color = '#4CAF50'  

    # Plot point x
    ax.scatter(x, 1, color=dot_color, edgecolors='#4A6B9C', 
               s=150, zorder=3, linewidths=1.5)

    # Padding
    padding = (max - min) * 0.05
    ax.set_xlim(min - padding, max + padding)

    ax.axis('off')  # Hide labels

    # Save the image exactly as requested
    plt.savefig(path, transparent=True, bbox_inches='tight', pad_inches=0)
    
    # Free memory
    plt.close(fig)

# Testing
if __name__ == "__main__":
    # Example 1: Green dot (Above Q3)
    create_gpa_sparkline(min=1.5, q1=2.5, median=3.0, q3=3.5, max=4.0, x=3.8, path='sparkline_green.png')
    
    # Example 2: Orange dot (Inside the Interquartile Range)
    create_gpa_sparkline(min=1.5, q1=2.5, median=3.0, q3=3.5, max=4.0, x=3.1, path='sparkline_orange.png')
    
    # Example 3: Red dot (Below Q1)
    create_gpa_sparkline(min=1.5, q1=2.5, median=3.0, q3=3.5, max=4.0, x=1.5, path='sparkline_red.png')